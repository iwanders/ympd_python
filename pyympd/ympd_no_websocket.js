
var WSA_poll_interval = 1000;  // ms, obtain status / heartbeat
var WSA_retry_interval = 3000; // ms, retry interval on connect failure

// doesn't really seem to be necessary?
var WSA_initial_connect_interval = 100; // ms, duration between creation and connect

function WebSocketAlternative(url) {
    var self = this;
    // These methods will be replaced.
    this.onopen = function(){
        console.log("onopen called while not set.");
        setTimeout(self.onclose, WSA_retry_interval);
    };
    this.onmessage = function(d){
        console.log("onmessage called while not set: " + d);
    };
    this.onclose = function(){
        console.log("onclose called while not set.");
        setTimeout(self.onclose, WSA_retry_interval);
    };

    // This passes a list of messages received over the 'websocket' into the
    // configured onmessage callback.
    this.ws_response_handler = function(data)
    {
        // console.log(data);
        $.each(data, function (id, z) {
            self.onmessage({data:z});
        });
    }

    // Sends data to the endpoint.
    this.send = function (req) {
        $.ajax({
            type: "POST",
            contentType : 'application/json',
            url: self._url,
            data: JSON.stringify({ws_msg:req}),
            dataType: 'json',
        }).success(self.ws_response_handler)
        .fail(function() {
            self.got_disconnected();
        });
    };

    // Got disconnected (a request failed) for some reason, stop the update
    // loop and retry after the interval.
    this.got_disconnected = function()
    {
        console.log("Got disconnected!");
        self._state = "disconnected";
        clearInterval(self.updater);

        // call retry after the retry interval.
        setTimeout(self.onclose, WSA_retry_interval);
    }

    // We have established a connection, tell the registered onopen method
    // that we did that, and set the poll interval.
    this.connection_established = function()
    {
        self._state = "connected";
        self.onopen();
        clearInterval(self.updater);
        self.updater = setInterval(function () {self.update();}, WSA_poll_interval);
    }

    // If not connected, this method attempts to connect.
    // If alrleady connected, it sends a 'beat' event, which basically tells
    // the endpoint to send the status, normally done by the pacemaker.
    this.update = function()
    {
        if (self._state == "not_connected")
        {
            $.ajax({
                type: "POST",
                contentType : 'application/json',
                url: self._url,
                data: JSON.stringify({ws_open:""}),  // send 'open'
                dataType: 'json',
            }).success(function(data) {
                self.connection_established();  // start the application / set opened state
                self.ws_response_handler(data);  // process the first messages.
            }).fail(function (){
                self.got_disconnected();  // something went wrong.
            });
            return;
        }
        if (self._state == "connected")
        {
            $.ajax({
                type: "POST",
                contentType : 'application/json',
                url: self._url,
                data: JSON.stringify({cmd_beat:[]}), // send 'beat'
                dataType: 'json',
            }).success(self.ws_response_handler)
            .fail(function() {
                self.got_disconnected();
            });
        }
        if (self._state == "disconnected")
        {
            console.log("Update called before update loop was killed.");
        }
    }

    // Replace 'ws' with 'http', rest of path is the same.
    // wss:// -> https://, ws:// -> http://
    var pcol = "http";
    var url = pcol + url.substr(2);

    self._url = url;
    self._state = "not_connected";

    // Initial connect interval sets time between creation of this object and
    // the first call of update = the connection phase.
    // This can be short, but needs to be long enough for the methods to be set.
    // can be practically zero.
    self.updater = setInterval(function () {
        self.update();
    }, WSA_initial_connect_interval);
};