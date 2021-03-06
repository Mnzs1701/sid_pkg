#!/usr/bin/env python

import rospy
from geometry_msgs.msg import Twist

import RPi.GPIO as GPIO


# Set the GPIO modes
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

_FREQUENCY = 20
_PWMFREQUENCY = 50

def _clip(value, minimum, maximum):
    """Ensure value is between minimum and maximum."""

    if value < minimum:
        return minimum
    elif value > maximum:
        return maximum
    return value

class Servo:
    def __init__(self,servo_pin):
        self._servo_pin = servo_pin
        GPIO.setup(servo_pin,GPIO.OUT)
        self._servo_pwm = GPIO.PWM(servo_pin,_PWMFREQUENCY)
        rospy.loginfo("Reached servo init")

    def turn(self, angle):
        self.angle = angle
        self.duty = 10-((self.angle / 10) - 2)
        self._servo_pwm.start(self.duty)

        #rospy.loginfo("Servo Turn: [%f]"%(self.duty))
       
class Motor:
    def __init__(self, forward_pin, backward_pin):
        self._forward_pin = forward_pin
        self._backward_pin = backward_pin

        GPIO.setup(forward_pin, GPIO.OUT)
        GPIO.setup(backward_pin, GPIO.OUT)

        self._forward_pwm = GPIO.PWM(forward_pin, _FREQUENCY)
        self._backward_pwm = GPIO.PWM(backward_pin, _FREQUENCY)

    def move(self, speed_percent):
        speed = _clip(abs(speed_percent), 0, 100)

        # Positive speeds move wheels forward, negative speeds 
        # move wheels backward
        if speed_percent < 0:
            self._backward_pwm.start(speed)
            self._forward_pwm.start(0)
        else:
            self._forward_pwm.start(speed)
            self._backward_pwm.start(0)

class Driver:
    def __init__(self):
        rospy.init_node('driver')

        self._last_received = rospy.get_time()
        self._timeout = rospy.get_param('~timeout', 2)
        self._rate = rospy.get_param('~rate', 10)
        self._max_speed = rospy.get_param('~max_speed', 1)
        self._wheel_base = rospy.get_param('~wheel_base', 1)

        # Assign pins to motors. These may be distributed
        # differently depending on how you've built your robot
        self._left_motor = Motor(10, 9)
        self._right_motor = Motor(8, 7)
        self._servo = Servo(17)

        self._left_speed_percent = 0
        self._right_speed_percent = 0
        self._servo_angle = 57

        # Setup subscriber for velocity twist message
        rospy.Subscriber(
            "/cmd_vel", Twist, self.velocity_received_callback)

        rospy.loginfo("Reached subscriber init")


    def velocity_received_callback(self, message):
        """Handle new velocity command message."""

        self._last_received = rospy.get_time()

        # Extract linear and angular velocities from the message
        linear = message.linear.x
        angular = message.angular.z
        
        #rospy.loginfo("Received a /cmd_vel message!")
        #rospy.loginfo("Linear Components: [%f, %f, %f]"%(message.linear.x, message.linear.y, message.linear.z))
        #rospy.loginfo("Angular Components: [%f, %f, %f]"%(message.angular.x, message.angular.y, message.angular.z))

        # Calculate wheel speeds in m/s
        left_speed = linear - angular*self._wheel_base/2
        right_speed = linear + angular*self._wheel_base/2

        # Ideally we'd now use the desired wheel speeds along
        # with data from wheel speed sensors to come up with the
        # power we need to apply to the wheels, but we don't have
        # wheel speed sensors. Instead, we'll simply convert m/s
        # into percent of maximum wheel speed, which gives us a
        # duty cycle that we can apply to each motor.
        self._servo_angle = ((angular*20)+57)
        
        #rospy.loginfo("Servo Angle: [%f]"%(self._servo_angle))
       
        self._left_speed_percent = (100 * left_speed/self._max_speed)
        self._right_speed_percent = (100 * right_speed/self._max_speed)

    def run(self):
        """The control loop of the driver."""

        rate = rospy.Rate(self._rate)

        while not rospy.is_shutdown():
            # If we haven't received new commands for a while, we
            # may have lost contact with the commander-- stop
            # moving
            delay = rospy.get_time() - self._last_received
            if delay < self._timeout:
                self._left_motor.move(self._left_speed_percent)
                self._right_motor.move(self._right_speed_percent)
                self._servo.turn(self._servo_angle)
            else:
                self._left_motor.move(0)
                self._right_motor.move(0)
                self._servo.turn(60)
            rate.sleep()

def main():
    driver = Driver()

    # Run driver. This will block
    driver.run()

if __name__ == '__main__':
    main()

#JRMH2911
