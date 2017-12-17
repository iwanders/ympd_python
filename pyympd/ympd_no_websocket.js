
function WebSocketAlternative(url) {
    pcol = "http";
    url = pcol + url.substr(2);
    console.log("< " + url);
    this._url = url;
    var _state = "not_connected";
    this.readyState = 0;
    this.onopen = function(){};
    this.onmessage = function(d){
        console.log("Onmessage not changed: " + d);
        };
    this.onclose = function(){};

    this.ws_response_handler = function(data)
    {
        // console.log(data);
        $.each(data, function (id, z) {
            onmessage({data:z});
        });
    }

    this.send = function (req) {
        $.ajax({
            type: "POST",
            contentType : 'application/json',
            url: this._url,
            data: JSON.stringify({ws_msg:req}),
            dataType: 'json',
        }).success(ws_response_handler)
        .fail(function() {
            console.log("fail");
        });
    };

    this.update = function()
    {
        console.log("Update: " + _state);
        if (_state == "not_connected")
        {
            $.ajax({
                type: "POST",
                contentType : 'application/json',
                url: this._url,
                data: JSON.stringify({ws_open:""}),
                dataType: 'json',
            }).success(function(data) {
                console.log( "opened websocket" );
                this._state = "connected";
                this.readyState  = 1;
                onopen();
            });
        }
        if (_state == "connected")
        {
            $.ajax({
                type: "POST",
                contentType : 'application/json',
                url: this._url,
                data: JSON.stringify({ws_get:[]}),
                dataType: 'json',
            }).success(ws_response_handler)
            .fail(function() {
                this._state = "disconnected";
                onclose();
            });
        }
    }
    setInterval(function () {this.update();},5000);
    return this;
};