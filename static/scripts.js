var last_msg_secs = 0;

function handle_msg (ev) {
  console.log (ev.data)
//  var msg = JSON.parse(ev.data);
//  var msg_pretty = JSON.stringify(msg, null, 2);
//  $("#last_msg").html(msg_pretty);

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
//    setup_watchdog();
  }
});
