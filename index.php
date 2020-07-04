<?php

require_once("app.php");

$anon_ok = 1;

pstart ();

$body .= "<div>\n";
$body .= mklink ("home", "/");
$body .= "</div>\n";

$body .= "<p>hello</p>\n";

$wss_host = $cfg['external_name'];
$wss_port = $cfg['wss_port'];

$wss_url = sprintf ("wss://%s:%d", $wss_host, $wss_port);

$extra_scripts .= sprintf ("var wss_url = '%s';\n", h($wss_url));

$body .= "<canvas id='temp_canvas' width='320' height='240'></canvas>\n";

$body .= "<p>world</p>\n";

pfinish ();
