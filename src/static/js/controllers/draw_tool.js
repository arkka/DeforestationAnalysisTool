
/*

var PolygonEditTool = Backbone.View.extend({

    initialize: function() {
        _.bindAll(this, 'add_vertex', 'create_polygon', 'reset', 'editing_state', '_add_vertex');
        this.mapview = this.options.mapview;
        this.map = this.mapview.map;
        this.reset();

        this.image = new google.maps.MarkerImage('/static/img/sprite.png',
                    new google.maps.Size(11, 11),
                    new google.maps.Point(0,52),
                    new google.maps.Point(5, 5)
        );
    },

});
*/

var PolygonDrawTool = Backbone.View.extend({

    initialize: function() {
        _.bindAll(this, 'add_vertex', 'create_polygon', 'reset', 'editing_state', '_add_vertex', 'edit_polygon');
        this.mapview = this.options.mapview;
        this.map = this.mapview.map;
        this.reset();

        this.image = new google.maps.MarkerImage('/static/img/sprite.png',
                    new google.maps.Size(11, 11),
                    new google.maps.Point(0,52),
                    new google.maps.Point(5, 5)
        );
    },

    editing_state: function(editing) {
        if(editing) {
            this.mapview.bind('click', this.add_vertex);
        } else {
            this.reset();
            this.mapview.unbind('click', this.add_vertex);
        }
    },


    reset: function() {
        if(this.polyline !== undefined) {
            this.polyline.setMap(null);
            delete this.polyline;
        }
        if(this.markers !== undefined) {
            _.each(this.markers, function(m) {
                m.setMap(null);
            });
        }
        this.markers = [];
        this.vertex = [];
        this.polyline = new google.maps.Polyline({
          path:[],
          strokeColor: "#DC143C",
          strokeOpacity: 0.8,
          strokeWeight: 2,
          map: this.map
        });
    },

    edit_polygon: function(polygon) {
        var self = this;
        var paths = polygon.paths();
        self.reset();

        _.each(paths, function(path, path_index) {
            _.each(path, function(p, i) {
                var marker = new google.maps.Marker({position:
                    p,
                    map: self.map,
                    icon: self.image,
                    draggable: true,
                    flat : true
                });
                marker.path_index = path_index;
                marker.index = i;
                self.markers.push(marker);
                google.maps.event.addListener(marker, "dragend", function(e) {
                    polygon.update_pos(marker.path_index, 
                        marker.index, [e.latLng.lat(), e.latLng.lng()]);
                    polygon.save();
                });

            });
        });

    },

    _add_vertex: function(latLng) {
        var marker = new google.maps.Marker({position:
                latLng,
                map: this.map,
                icon: this.image,
                draggable: true
                });

        marker.index = this.vertex.length;
        this.markers.push(marker);
        this.vertex.push(latLng);
        this.polyline.setPath(this.vertex);
        return marker;
    },

    add_vertex: function(e) {
        var latLng = e.latLng;
        var marker = this._add_vertex(latLng);
        var self = this;
        if (this.vertex.length === 1) {
            google.maps.event.addListener(marker, "dblclick", function() {
                self.create_polygon(self.vertex);
                self.reset();
            });
        }
    },

    create_polygon: function(vertex) {
        var type = Polygon.prototype.DEGRADATION;
        if(this.selected_poly_type === "def") {
            type = Polygon.prototype.DEFORESTATION;
        }
        var v = _.map(vertex, function(p) { return [p.lat(), p.lng()]; });
        this.trigger('polygon', {paths: [v], type: type});
    },

    poly_type: function(type) {
        console.log("selected type", type);
        this.selected_poly_type = type;
    }


});