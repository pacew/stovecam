<?php

require_once("app.php");

$anon_ok = 1;

pstart ();

$wss_host = $cfg['external_name'];
$wss_port = $cfg['wss_port'];

$wss_url = sprintf ("wss://%s:%d", $wss_host, $wss_port);

$extra_scripts .= sprintf ("var wss_url = '%s';\n", h($wss_url));

$factor = 20;
$w = 32 * $factor;
$h = 24 * $factor;
$body .= sprintf ("<canvas id='temp_canvas'"
    ." width='%d' height='%d'></canvas>\n",
    $w, $h);

$body .= "<div>"
      ." mouse temp"
      ." <span id='mouse_temp'>temp</span>"
      ."</div>\n";

$body .= "<div>"
      ." monitor temp"
      ." <span id='monitor_temp'>temp</span>"
      ."</div>\n";



pfinish ();
