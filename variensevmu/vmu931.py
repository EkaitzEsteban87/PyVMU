import serial
import time
import struct
import logging
import variensevmu.messages as messages


class VMU931Parser(object):
    def __init__(self,
                 device="/dev/tty.usbmodem1411",
                 accelerometer=False,
                 magnetometer=False,
                 gyroscope=False,
                 euler=False,
                 quaternion=False,
                 heading=False
                 ):
        """
        Opens connection to VMU931 device
        :param device: 
        """
        self.ser = serial.Serial(device)
        self.device_status = None
        self.parse()

        self.set_accelerometer(accelerometer)
        self.set_magnetometer(magnetometer)
        self.set_gyroscope(gyroscope)
        self.set_euler(euler)
        self.set_quaternion(quaternion)
        self.set_heading(heading)

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.ser.close()

    def set_quaternion(self, state):
        """
        Enable streaming of quaternion data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.quaternions_streaming != state:
            self.toggle_quaternion()

    def set_euler(self, state):
        """
        Enable/disable streaming of euler angle data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.euler_streaming != state:
            self.toggle_euler()

    def set_accelerometer(self, state):
        """
        Enable/disable streaming of accelerometer data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.accelerometer_streaming != state:
            self.toggle_accelerometer()

    def set_magnetometer(self, state):
        """
        Enable/disable streaming of magnetometer data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.magnetometer_streaming != state:
            self.toggle_magnetometer()

    def set_gyroscope(self, state):
        """
        Enabled/disable streaming of gyroscope data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.gyroscope_streaming != state:
            self.toggle_gyroscope()

    def set_heading(self, state):
        """
        Enable/disable streaming of compass heading data.
        :param state: 
        :return: 
        """
        assert self.device_status is not None, "Device status is not set"

        if self.device_status.heading_streaming != state:
            self.toggle_heading()


    def toggle_quaternion(self):
        """
        Toggles quaternion output from the VMU931 device
        :return: 
        """
        self.send_message("varq")

    def toggle_euler(self):
        """
        Toggles quaternion output from the VMU931 device.
        :return: 
        """
        self.send_message("vare")

    def toggle_heading(self):
        """
        Toggles heading output from the VMU931 device.
        :return: 
        """
        self.send_message("varh")

    def toggle_accelerometer(self):
        """
        Toggles accelerometer output from the VMU931 device.
        :return: 
        """
        self.send_message("vara")

    def toggle_gyroscope(self):
        """
        Toggles gyroscope output from the VMU931 device.
        :return: 
        """
        self.send_message("varg")

    def toggle_magnetometer(self):
        """
        Toggles magnetometer output from the VMU931 device.
        :return: 
        """
        self.send_message("varc")

    def set_gyroscope_resolution(self, resolution):
        """
        Sets the gyroscope output resolution of the VMU931 device.
        :param resolution: 250, 500, 1000 or 2000.
        :return: 
        """
        assert resolution in (250, 500, 1000, 2000), "Invalid gyroscope resolution, must be 250, 500, 1000 or 2000"

        mapping = {250: 0, 500: 1, 1000: 2, 2000: 3}
        command = "var{}".format(mapping[resolution])
        self.send_message(command)

    def set_accelerometer_resolution(self, resolution):
        """
        Sets the accelerometer output resolution of the VMU931 device.
        :param resolution: 2, 4, 8 or 16. 
        :return: 
        """
        assert resolution in (2, 4, 8, 16), "Invalid accelerometer resolution, must be 2, 4, 8 or 18"

        mapping = {2: 4, 4: 5, 8: 6, 16: 7}
        command = "var{}".format(mapping[resolution])
        self.send_message(command)

    def send_message(self, message, update_status=True):
        """
        Sends a message to the VMU931 device, with 5ms delay between each character. 
        :param message: Message to send to device
        :param update_status: Update sensor status after message send (defaults to True)
        :return: 
        """
        bmessage = message.encode('ascii')

        # bytes must be sent with 1ms+ interval to be recognised by device.
        for c in bmessage:
            bs = bytes([c])
            self.ser.write(bs)
            logging.debug("Sent {}".format(bs))
            time.sleep(0.01)
        time.sleep(0.05)

        if update_status:
            self.request_status()
            time.sleep(0.200)

    def request_status(self):
        """
        Request a new status packet from the VMU931
        :return: 
        """

        # We don't want to update the status again after sending the message, otherwise we'd be in an infinite loop.
        logging.info("Requesting status update")
        self.send_message("vars", update_status=False)

    def parse(self, callback=None):
        """
        Parses a single packet from the VMU931 device, returning a namedtuple. Typically called multiple times from
        within a loop.

        If device status is currently known, we wait for an incoming status packet and parse it. This method will block
        until status is recieved (so that we're in a known state)

        :param callback: Method to call after processing each packet
        :return: processed packet
        """

        # If we don't know the current device status, request it
        if self.device_status is None:
            self.request_status()

        # Loop until we get a status packet. Will normally only loop once per call.
        while True:
            # Find start of data message -- we might start processing data mid-stream so need to synchronise.
            # We are looking for the magic byte 0x01. There's a chance that this will be randomly encountered, but
            # we also check the footer value.
            message_start = self.ser.read()[0]
            while message_start != 0x01:
                logging.debug("Skipping invalid message_start, got {} expected 0x01".format(hex(message_start)))
                message_start = self.ser.read()[0]
                continue

            message_size = self.ser.read()[0] - 4  # Unsure why we have to subtract 4bytes from this... but we do.
            logging.debug("Message size: {}".format(message_size))
            message_type = chr(self.ser.read()[0])
            logging.debug("Message type: {}".format(message_type))
            message_text = self.ser.read(message_size)
            message_end = self.ser.read()[0]

            # If we have an invalid footer, skip this packet, otherwise continue.
            if message_end != 0x04:
                logging.warning(
                    "Invalid Message footer (was {}, expected 0x04), skipping this packet".format(message_end))
            else:
                data = None

                if message_type == 'e':
                    logging.info("Parsing Euler")
                    data = VMU931Parser.parse_euler(message_text)
                elif message_type == 'q':
                    logging.info("Parsing Quaternion")
                    data = VMU931Parser.parse_quaternion(message_text)
                elif message_type == 'h':
                    logging.info("Parsing Heading")
                    data = VMU931Parser.parse_heading(message_text)
                elif message_type == 'a':
                    logging.info("Parsing Accelerometer")
                    data = VMU931Parser.parse_accelerometer(message_text)
                elif message_type == 'g':
                    logging.info("Parsing Gyroscope")
                    data = VMU931Parser.parse_gyroscope(message_text)
                elif message_type == 'c':
                    logging.info("Parsing Magnetometer")
                    data = VMU931Parser.parse_magnetometer(message_text)
                elif message_type == 's':
                    logging.info("Parsing status message")
                    data = VMU931Parser.parse_status(message_text)
                    self.device_status = data
                else:
                    logging.warning("No parser for {}".format(message_type))

                if self.device_status is not None:
                    if callback is not None and data is not None:
                        callback(data)
                    return data

    @staticmethod
    def parse_status(data):
        """
        Parse the contents of a status message according to the VMU931 User Guide
        (http://variense.com/Docs/VMU931/VMU931_UserGuide.pdf)
        :param data: Bytes to process
        :return: Device Status
        """
        status, res, low_output, data = struct.unpack(">BBBI", data[:7])

        mag_status = status & 0b00000100 != 0
        gyro_status = status & 0b00000010 != 0
        acc_status = status & 0b00000001 != 0

        gyro_res = None

        if res & 0b10000000 != 0:
            gyro_res = 2000
        elif res & 0b01000000 != 0:
            gyro_res = 1000
        elif res & 0b00100000 != 0:
            gyro_res = 500
        elif res & 0b00010000 != 0:
            gyro_res = 250

        acc_res = None

        if res & 0b00001000 != 0:
            acc_res = 16
        elif res & 0b000000100 != 0:
            acc_res = 8
        elif res & 0b00000010 != 0:
            acc_res = 4
        elif res & 0b00000001 != 0:
            acc_res = 2

        low_output_rate = low_output & 0b00000001 != 0

        heading_streaming = data & 0b01000000 != 0
        euler_streaming = data & 0b00010000 != 0
        mag_streaming = data & 0b00001000 != 0
        quat_streaming = data & 0b00000100 != 0
        gyro_streaming = data & 0b00000010 != 0
        acc_streaming = data & 0b00000001 != 0

        return messages.Status(
            magnetometer_enabled=mag_status,
            gyroscope_enabled=gyro_status,
            accelerometer_enabled=acc_status,
            gyroscope_resolution=gyro_res,
            accelerometer_resolution=acc_res,
            low_output_rate=low_output_rate,
            heading_streaming=heading_streaming,
            euler_streaming=euler_streaming,
            magnetometer_streaming=mag_streaming,
            quaternions_streaming=quat_streaming,
            gyroscope_streaming=gyro_streaming,
            accelerometer_streaming=acc_streaming
        )

    @staticmethod
    def parse_quaternion(data):
        ts, w, x, y, z = struct.unpack(">Iffff", data[:20])
        return messages.Quaternion(timestamp=ts, w=w, x=x, y=y, z=z)

    @staticmethod
    def parse_euler(data):
        ts, x, y, z = struct.unpack(">Ifff", data[:16])
        return messages.Euler(timestamp=ts, x=x, y=y, z=z)

    @staticmethod
    def parse_accelerometer(data):
        ts, x, y, z = struct.unpack(">Ifff", data[:16])
        return messages.Accelerometer(timestamp=ts, x=x, y=y, z=z)

    @staticmethod
    def parse_magnetometer(data):
        ts, x, y, z = struct.unpack(">Ifff", data[:16])
        return messages.Magnetometer(timestamp=ts, x=x, y=y, z=z)

    @staticmethod
    def parse_gyroscope(data):
        ts, x, y, z = struct.unpack(">Ifff", data[:16])
        return messages.Gyroscope(timestamp=ts, x=x, y=y, z=z)

    @staticmethod
    def parse_heading(data):
        ts, h = struct.unpack(">If", data[:8])
        return messages.Heading(timestamp=ts, h=h)
