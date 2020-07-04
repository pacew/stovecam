function lscale_clamp (val, from_left, from_right, to_left, to_right) {
  if (from_left == from_right)
    return (to_right);

  var x = (val - from_left)
      / (from_right - from_left)
      * (to_right - to_left)
      + to_left;
  if (to_left < to_right) {
    if (x < to_left)
      x = to_left;
    if (x > to_right)
      x = to_right;
  } else {
    if (x < to_right)
      x = to_right;
    if (x > to_left)
      x = to_left;
  }
  return (x);
}


var temps;

function display_temps(temps) {
  var mintemp = temps[0];
  var maxtemp = temps[0]
  for (var idx = 0; idx < 768; idx++) {
    if (temps[idx] < mintemp)
      mintemp = temps[idx];
    if (temps[idx] > maxtemp)
      maxtemp = temps[idx];
  }

  var screen_canvas = document.getElementById("temp_canvas");
  var ctx = screen_canvas.getContext("2d");

  var mult = Math.floor (screen_canvas.width / 32)

  for (var row = 0; row < 24; row++) {
    for (var col = 0; col < 32; col++) {
      var pnum = (23-row) * 32 + col
      var temp = temps[pnum]
      
      var h = lscale_clamp(temp, mintemp, maxtemp, 150, 359);
      var s = .9;
      var v = 1;
      ctx.fillStyle = "hsl("+h+",100%,70%)"
      ctx.fillRect(col*mult, row*mult, mult, mult);
    }
  }
}


var last_msg_secs = 0;

function handle_msg (ev) {
  var msg = JSON.parse(ev.data);

  temps = msg.img
  display_temps (temps)

  last_msg_secs = Date.now() / 1000.0;

}

var sock = null;

function maintain_connection () {
  if (sock && sock.readyState == WebSocket.CLOSED)
      sock = null;

  if (sock)
    return;

  console.log("connect to", wss_url);
  $("#wss_url").html(wss_url);
  sock = new WebSocket(wss_url);
  sock.onmessage = handle_msg;
}

function do_watchdog() {
  var now = Date.now() / 1000.0;
  var delta = now - last_msg_secs;

  if (delta < 3) {
    $("#wss_not_running").hide();
  } else {
    $("#wss_not_running").show();
    maintain_connection ();
  }
}


function setup_watchdog() {
    window.setInterval (do_watchdog, 1000);
}


$(function () {
  console.log("starting", window.wss_url)
  if (window.wss_url) {
    maintain_connection ();
    setup_watchdog();
  }
});
