# encoding: utf-8

import datetime
import logging
import os
import simplejson as json
from shutil import copyfile
import sys

from google.appengine.api import urlfetch
from google.appengine.api import users

sys.modules['ssl'] = None

try:
  from flask import render_template, flash, url_for, redirect, abort, request, make_response
except:
  # nose tests require zipped packages to be manually loaded
  import zipimport
  gflags = zipimport.zipimporter('packages/gflags.zip').load_module('gflags') 
  jinja2 = zipimport.zipimporter('packages/jinja2.zip').load_module('jinja2')  
  flask = zipimport.zipimporter('packages/flask.zip').load_module('flask')
  wtforms = zipimport.zipimporter('packages/wtforms.zip').load_module('wtforms')

from application.time_utils import timestamp, past_month_range

from decorators import login_required, admin_required
from forms import ExampleForm
from application.ee_bridge import NDFI, EELandsat, get_modis_thumbnail

from app import app

from models import Report, User, Error
from google.appengine.api import memcache
from google.appengine.ext.db import Key

from application import settings

def default_maps():
    maps = []
    r = Report.current() 
    logging.info("report " + unicode(r))
    landsat = EELandsat()
    ndfi = NDFI(past_month_range(r.start), r.range())

    d = landsat.mapid(timestamp(r.start), datetime.datetime.now())
    maps.append({'data' :d, 'info': 'LANDSAT/L7_L1T'})
    """
    d = landsat.mapid(*past_month_range(r.start))
    maps.append({'data' :d, 'info': 'LANDSAT/L7_L1T-old'})
    """
    #d = ndfi.mapid2()
    #if d: maps.append({'data' :d, 'info': 'ndfi difference'})
    d = ndfi.smaid()
    if d: maps.append({'data': d, 'info': 'SMA'})
    d = ndfi.rgb1id()
    if d: maps.append({'data': d, 'info': 'RGB'})
    d = ndfi.ndfi0id()
    if d: maps.append({'data': d, 'info': 'NDFI T0'})
    d = ndfi.ndfi1id()
    if d: maps.append({'data' :d, 'info': 'NDFI T1'})
    d = ndfi.baseline(r.base_map())
    if d: maps.append({'data' :d, 'info': 'Baseline'})
    d = ndfi.rgb0id()
    if d: maps.append({'data': d, 'info': 'Previous RGB'})
    return maps

def get_or_create_user():
    user = users.get_current_user()
    u = User.get_user(user)
    if not u and users.is_current_user_admin():
        u = User(user=user, role='admin')
        u.put()
    return u

@app.route('/')
def start():
    return redirect('/analysis')
    
@app.route('/analysis')
@login_required
def home(cell_path=None):
    maps = memcache.get('default_maps')
    if maps:
        maps = json.loads(maps)
    else:
        maps = default_maps()
        memcache.add(key='default_maps', value=json.dumps(maps), time=60*10)

    # send only the active report
    reports = json.dumps([Report.current().as_dict()])
    u = get_or_create_user()
    if not u:
        abort(403)

    logout_url = users.create_logout_url('/')
    return render_template('home.html',
            reports_json=reports,
            user=u,
            maps=maps,
            polygons_table=settings.FT_TABLE_ID,
            logout_url=logout_url)



@app.route('/vis')
@login_required
def vis():
    u = get_or_create_user()
    if not u:
        abort(403)

    logout_url = users.create_logout_url('/')
    #TODO show only finished
    reports = [x.as_dict() for x in Report.all().filter("finished =", True).order("start")]
    return render_template('vis/index.html',
            user=u,
            logout_url=logout_url,
            polygons_table=settings.FT_TABLE_ID,
            reports=json.dumps(reports))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/error_track',  methods=['GET', 'POST'])
def error_track():
    d = request.form
    logging.info(request.form)
    Error(msg=d['msg'], url=d['url'], line=d['line'], user=users.get_current_user()).put()
    return 'thanks'

@app.route('/tiles/<path:tile_path>')
def tiles(tile_path):
    """ serve static tiles """
    # save needed tiles
    if False:
        base = os.path.dirname(tile_path)
        try:
            os.makedirs("static/tiles/" + base)
        except OSError:
            pass #java rocks
        copyfile("static/maps/%s" % tile_path, "static/tiles/%s" % tile_path)
    return redirect('/static/tiles/%s' % tile_path)
    #return redirect('/static/maps/%s' % tile_path)


EARTH_ENGINE_TILE_SERVER = settings.EE_TILE_SERVER

@app.route('/ee/tiles/<path:tile_path>')
def earth_engine_tile_proyx(tile_path):
    token = request.args.get('token', '')
    if not token:
        abort(401)
    result = urlfetch.fetch(EARTH_ENGINE_TILE_SERVER + tile_path + '?token='+ token, deadline=10)

    response = make_response(result.content)
    response.headers['Content-Type'] = result.headers['Content-Type']
    return response

@app.route('/proxy/<path:tile_path>')
def proxy(tile_path):
    result = urlfetch.fetch('https://'+ tile_path, deadline=10)
    response = make_response(result.content)
    response.headers['Content-Type'] = result.headers['Content-Type']
    response.headers['Expires'] = 'Thu, 15 Apr 2020 20:00:00 GMT'
    return response

@app.route('/admin_only')
@admin_required
def admin_only():
    """This view requires an admin account"""
    return 'Super-seekrit admin page.'


@app.route('/_ah/warmup')
def warmup():
    """App Engine warmup handler
    See http://code.google.com/appengine/docs/python/config/appconfig.html#Warming_Requests

    """
    return ''

@app.route('/picker')
def picker():
    cell = request.args.get('cell','')
    scene = 'MOD09GA/MOD09GA_005_2010_01_01'
    bands = 'sur_refl_b01,sur_refl_b04,sur_refl_b03'
    gain = 0.1
    if scene:
       result = get_modis_thumbnail(scene, cell, bands, gain)
    else:
       result = {'thumbid': '', 'token': ''}
    return render_template('picker.html', **result)
