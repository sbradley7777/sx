#!/usr/bin/env python
"""
The Logger Class will log messages to console or to a file. If logged
to console then text will colorize the message type.

@author    :  Shane Bradley
@contact   :  sbradley@redhat.com
@version   :  2.16
@copyright :  GPLv2
"""
import logging
import os
import sys

class LogWriter :
    """
    The Logger Class will log messages to console or to a file.

    @cvar STATUS_LEVEL: Int that represents the message level.
    @type STATUS_LEVEL: Int
    @cvar INFO_LEVEL: Int that represents the message level.
    @type INFO_LEVEL: Int
    @cvar ERROR_LEVEL: Int that represents the message level.
    @type ERROR_LEVEL: Int
    @cvar WARNING_LEVEL: Int that represents the message level.
    @type WARNING_LEVEL: Int
    @cvar CRITICAL_LEVEL: Int that represents the message level.
    @type CRITICAL_LEVEL: Int
    @cvar DEBUG_LEVEL: Int that represents the message level.
    @type DEBUG_LEVEL: Int
    @cvar DISABLE_LOGGING: Int that represents turning off all logging.
    @type DISABLE_LOGGING: Int
    """
    CRITICAL_LEVEL = logging.CRITICAL        #50
    ERROR_LEVEL    = logging.ERROR           #40
    WARNING_LEVEL  = logging.WARN            #30
    # FAILED_LEVEL   = logging.WARN + 1        #31
    STATUS_LEVEL   = logging.INFO + 2        #22
    # PASSED_LEVEL   = logging.INFO + 1        #21
    INFO_LEVEL     = logging.INFO            #20
    DEBUG_LEVEL    = logging.DEBUG           #10
    DISABLE_LOGGING = logging.NOTSET         #0

    def __init__(self, loggerName, loglevel, format, logtoFile=False,
                 disableConsoleLog=False):
        """
        Sets up logger object for writing to files or console.

        @param loggerName: The name that will used for logger.
        @type loggerName: String
        @param loglevel: Level of messages that will be logged.
        @type loglevel: Int
        @param format: The format that will be used based on python
        loggging module.
        @type format: String
        @param logtoFile: This will enable logging to file
        "/tmp/<loggername>.log"
        @type logtoFile: Boolean
        @param disableConsoleLog: This will disable writing to console
        @type disableConsoleLog: Boolean
        """
        self.__loggerName = loggerName
        # add new custom logging level
        # logging.PASSED = LogWriter.PASSED_LEVEL
        # logging.FAILED = LogWriter.FAILED_LEVEL
        # logging.addLevelName(logging.PASSED, "PASSED")
        # logging.addLevelName(logging.FAILED, "FAILED")
        logging.STATUS = LogWriter.STATUS_LEVEL
        logging.addLevelName(logging.STATUS, "STATUS")
        logger = logging.getLogger(self.__loggerName)
        # Create a function for the STATUS_LEVEL since not defined by
        # python. This means you can call it like the other predefined message
        # functions. Example: logging.getLogger("loggerName").status(message)
        setattr(logger, "status", lambda *args: logger.log(LogWriter.STATUS_LEVEL, *args))
        # set formatter
        formatter = logging.Formatter(format)
        # get logger and set format
        self.__logwriter = logging.getLogger(loggerName)
        self.__logwriter.setLevel(loglevel)

        # set the handler for writing to standard out
        self.__hdlrConsole = None
        if disableConsoleLog:
            # set standard out to blackhole
            sys.stdout = open('/dev/null', 'w')
        self.__hdlrConsole = StreamHandlerColorized(sys.stdout)
        self.__hdlrConsole.setFormatter(formatter)
        self.__logwriter.addHandler(self.__hdlrConsole)

        # set the handler for writing to file if enabled
        self.__pathToLogFile = ""
        self.__hdlrFile = None
        if (logtoFile) :
            pathToLogFile = "/tmp/%s.log" %(loggerName)
            if ((os.access(pathToLogFile, os.W_OK)) or (not os.path.exists(pathToLogFile))):
                self.__pathToLogFile = pathToLogFile
                self.__hdlrFile = logging.FileHandler(self.__pathToLogFile)
                self.__hdlrFile.setFormatter(formatter)
                self.__logwriter.addHandler(self.__hdlrFile)
            else:
                message = "There was permission problem accessing the write attributes for the log file: %s." %(pathToLogFile)
                self.__logwriter.error(message)

    def getLogWriter(self) :
        """
        Returns the logger that was setup for this object.

        @return: Returns the logger object.
        @rtype: Logger
        """
        return self.__logwriter

    def getPathToLogFile(self):
        """
        Returns path to the log file. Will return empty string if
        logging to file is not enabled or access to file to write
        fails.

        @return: Returns path to the log file. Will return empty
        string if logging to file is not enabled or access to file to
        write fails.
        @rtype: String
        """
        return self.__pathToLogFile

    def removeHandlers(self) :
        """
        Removes all the handlers for this logger.
        """
        if (not self.__hdlrConsole == None) :
            self.__logwriter.removeHandler(self.__hdlrConsole)
            self.__hdlrConsole.flush()
            self.__hdlrConsole.close()
            #print logging._handlers

        if (not self.__hdlrFile == None) :
            self.__logwriter.removeHandler(self.__hdlrFile)
            self.__hdlrFile.close()

class StreamHandlerColorized(logging.StreamHandler):
    """
    A StreamHandler that colorized the message level of messsage
    written to std.out.

    These are bash shell colors: http://tldp.org/HOWTO/Bash-Prompt-HOWTO/x329.html

    @cvar CONSOLE_COLORS: Dictionary of string that reprensents the
    colors of console text. The following colors are valid:
    black, red, green, brown, blue, purple, cyan, lgray, gray, lred,
    lgreen, yellow, lblue, pink, lcyan, white.

    @type CONSOLE_COLORS: Dictionary

    """
    CONSOLE_COLORS = {"black":"30", "white":"1;37", "red":"31", "lred":"1;31",
                      "green":"32", "lgreen":"1;32", "blue":"34", "lblue":"1;34",
                      "gray":"1;30", "lgray":"37", "cyan":"36", "lcyan":"1;36",
                      "purple":"35", "brown":"33", "yellow":"1;33", "pink":"1;35"}


    def __colorizeText(self, text, color):
        """
        Return colored text to be written to console

        Links below explain what I am injecting into the string:

        http://tldp.org/HOWTO/Bash-Prompt-HOWTO/x329.html
        http://www.faqs.org/docs/abs/HTML/colorizing.html

        @return: String that includes the text string and color
        strings.
        @rtype: String
        @param text: The string that will have terminal bash color
        statements inserted into string to change foreground color.
        @type text: String
        @param color: The color that text should be colorized to.
        @type color: String
        """
        if (not StreamHandlerColorized.CONSOLE_COLORS.has_key(color)):
            return text
        fgColor = StreamHandlerColorized.CONSOLE_COLORS.get(color)
        opencol = "\033["
        closecol = "m"
        clear = opencol + "0" + closecol
        fg = opencol + fgColor + closecol
        for i in range((len("CRITICAL") + 1) - len(text)):
            text += " "
        return "%s%s%s" % (fg, text, clear)

    def emit(self, record):
        """
        The record is then written to the stream with a trailing
        newline. If the message or record contains a loglevel then the
        loglevel is colorized in the message.

        @param record: This is message that was passed and other
        logging information.
        @type record: record
        """
        try:
            msg = self.format(record)
            #find which message level this is
            colorizedMsg = None
            #if (msg.find("PASSED") >= 0) :
            #    colorizedMsg = self.__colorizeText("PASSED", "lblue")
            #    msg = msg.replace("PASSED", colorizedMsg, 1)
            # elif (msg.find("FAILED") >= 0) :
            #    colorizedMsg = self.__colorizeText("FAILED", "red")
            #    msg = msg.replace("FAILED", colorizedMsg, 1)

            if (msg.find("STATUS") >= 0) :
                colorizedMsg = self.__colorizeText("STATUS", "brown")
                msg = msg.replace("STATUS", colorizedMsg, 1)
            elif (msg.find("INFO") >= 0) :
                colorizedMsg = self.__colorizeText("INFO", "blue")
                msg = msg.replace("INFO", colorizedMsg, 1)
            elif (msg.find("ERROR") >= 0) :
                colorizedMsg = self.__colorizeText("ERROR", "red")
                msg = msg.replace("ERROR", colorizedMsg, 1)
            elif (msg.find("WARNING") >= 0) :
                colorizedMsg = self.__colorizeText("WARNING", "yellow")
                msg = msg.replace("WARNING", colorizedMsg, 1)
            elif (msg.find("CRITICAL") >= 0) :
                colorizedMsg = self.__colorizeText("CRITICAL", "lred")
                msg = msg.replace("CRITICAL", colorizedMsg, 1)
            elif (msg.find("DEBUG") >= 0) :
                colorizedMsg = self.__colorizeText("DEBUG", "purple")
                msg = msg.replace("DEBUG", colorizedMsg, 1)
            self.stream.write(msg + "\n")
            self.flush()
        except:
            self.handleError(record)


