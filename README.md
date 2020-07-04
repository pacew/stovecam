# stovecam

Work in progress.

A project to point an
[MLX90640](https://www.melexis.com/en/product/MLX90640/Far-Infrared-Thermal-Sensor-Array)
far infrared sensor array at my stove and display a beautiful web
interface that shows graphs of the current and projected temperatures
for pans on several burners at once.

The sensor is attached to a Raspberry PI, which spews multicast UDP
packets and serves websockets requests for the raw data.

Includes a port of the messy [MLX90640 C++
library](https://github.com/melexis/mlx90640-library) to pure python
(currently slightly less messy - but at least it doesn't busywait).

