<?php

require_once("app.php");

$anon_ok = 1;

pstart ();

$body .= "<div>\n";
$body .= mklink ("home", "/");
$body .= "</div>\n";

$body .= "<p>hello</p>\n";

$wss_host = "pi1.pacew.org";
$wss_port = 10555;

$wss_url = sprintf ("wss://%s:%d", $wss_host, $wss_port);

$extra_scripts .= sprintf ("var wss_url = '%s';\n", h($wss_url));

pfinish ();
