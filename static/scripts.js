var main_canvas;
var main_ctx;
var temps;

var monitor_x = 329;
var monitor_y = 121;


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


function line(x1, y1, x2, y2) {
  main_ctx.beginPath();
  main_ctx.moveTo(x1, y1)
  main_ctx.lineTo(x2, y2,)
  main_ctx.stroke();
}

function get_temp(row, col) {
  return temps[(23-row) * 32 + col]
}

function get_temp_pixels(x, y) {
  var row = Math.floor (y * 24 / main_canvas.height);
  var col = Math.floor (x * 32 / main_canvas.width);

  return temps[(23-row) * 32 + col]
}


function display_temps() {
  var mintemp = temps[0];
  var maxtemp = temps[0];
  var maxtemp_idx = 0;
  for (var idx = 0; idx < 768; idx++) {
    if (temps[idx] < mintemp)
      mintemp = temps[idx];
    if (temps[idx] > maxtemp) {
      maxtemp = temps[idx];
      maxtemp_idx = idx;
    }
  }

  mintemp = 75
  maxtemp = 500

  var mult = Math.floor (main_canvas.width / 32)

  for (var row = 0; row < 24; row++) {
    for (var col = 0; col < 32; col++) {
      var temp = get_temp (row, col)
      
      var shift = 60
      var lo = Math.log(mintemp - shift);
      var hi = Math.log(maxtemp - shift);
      var y = Math.log(temp - shift)

      var h = lscale_clamp(y, lo, hi, 150, 359);
      var s = .9;
      var v = 1;
      main_ctx.fillStyle = "hsl("+h+",100%,70%)"
      main_ctx.fillRect(col*mult, row*mult, mult, mult);
    }
  }
}

function do_monitor_temp() {
  main_ctx.fillStyle = "black";
  line(monitor_x - 10, monitor_y, monitor_x + 10, monitor_y);
  line(monitor_x, monitor_y - 10, monitor_x, monitor_y + 10);


  var t = get_temp_pixels (monitor_x, monitor_y);
  $("#monitor_temp").html(t);

}

function redraw () {
  display_temps();
  do_monitor_temp ();
}
  




var last_msg_secs = 0;

function handle_msg (ev) {
  var msg = JSON.parse(ev.data);

  temps = msg.img
  redraw ()

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

var mouse_x, mouse_y;

function do_mousemove(ev) {
  var rect = main_canvas.getBoundingClientRect();
  var x = ev.clientX - rect.left;
  var y = ev.clientY - rect.top;

  var t = get_temp_pixels (x, y);
  $("#mouse_temp").html(t);

}

function do_mousedown(ev) {
  var rect = main_canvas.getBoundingClientRect();
  var x = ev.clientX - rect.left;
  var y = ev.clientY - rect.top;

  monitor_x = x;
  monitor_y = y;

  redraw ();
}

function setup() {
  main_canvas = document.getElementById("temp_canvas");
  main_ctx = main_canvas.getContext("2d");
  
  main_canvas.addEventListener('mousemove', do_mousemove);
  main_canvas.addEventListener('mousedown', do_mousedown);
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
  setup ();

  console.log("starting", window.wss_url)
  if (window.wss_url) {
    maintain_connection ();
    setup_watchdog();
  }
});
