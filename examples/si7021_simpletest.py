"""
Initializes the sensor, gets and prints readings every two seconds.
"""
import time
import board
import adafruit_si7021

# Create library object using our Bus I2C port
i2c = board.I2C()
sensor = adafruit_si7021.SI7021(i2c)


while True:
    print("\nTemperature: %0.1f C" % sensor.temperature)
    print("Humidity: %0.1f %%" % sensor.relative_humidity)
    time.sleep(2)
