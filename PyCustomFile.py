# -------------------------------------------------------------------------------------------------------------------
#  PyCustomFile : Allows easy creation of custom files in Python by handling low level file operations
# -------------------------------------------------------------------------------------------------------------------
# 
# Author: Ashok Fernandez - https://github.com/ashokfernandez/
# Date  : 14 / 01 / 2014
# 
# Description: 
# Extending FileBase allows the user to create a custom filetype without worrying about low-level file operations
# and tracking changes that have happened on disc.
# Custom files are saved on disc with any given extension and can carry any python data with them by using the 
# setData method. The data stored using this method is pickled and saved in the file.
# Methods that are decorated with the @makesChanges decorator will set a flag that automatically tracks when the
# file has been changed from what it was on disc. If higher level methods only change the files data object using
# the setData method then all changes to the files python data object will be tracked.
# 
# Licence: 
# Copyright Ashok Fernandez 2013
# Released under the MIT license - http://opensource.org/licenses/MIT
# 
# Usage example: 
# See the bottom of this file. The demo can be run by running this file.
# -------------------------------------------------------------------------------------------------------------------

import functools            # Used for makesChanges method decorator
import watchdog.observers   # Track filesystem changes
import watchdog.events      # Handle filesystem events
import os                   # Access the filesystem

# Try to import cPickle and if it fails, fall back to plain old python pickle
try:
    import cPickle as pickle
except ImportError:
    import pickle


# --------------------------------------------------------------------------------------------------------------------
# EXCEPTIONS
# --------------------------------------------------------------------------------------------------------------------

class NotEnoughInfoOnFile(Exception):
    ''' Exception when there aren't enough parameters for the watchdog to initialise '''
    pass

class FileDeleted(Exception):
    ''' Exception that is thrown when the given file is deleted from the filesystem or moves to
    another folder '''
    pass

# --------------------------------------------------------------------------------------------------------------------
# DECORATORS
# --------------------------------------------------------------------------------------------------------------------

def makesChanges(func):
    ''' Decorator to wrap methods that will change the state of an instance. Used on methods that 
    would require the object to be saved to disk again after the method has been called. Calls the
    _changesMade() method of the object to update the internal change tracker.'''

    @functools.wraps(func)
    
    def trackChange(*args, **kwargs):
        # Track the change made to the object then continue on calling the method
        args[0]._changesMade()
        return func(*args, **kwargs)
    
    return trackChange


# --------------------------------------------------------------------------------------------------------------------
# CLASSES
# --------------------------------------------------------------------------------------------------------------------

class FileBaseWatchDog(watchdog.events.FileSystemEventHandler):
    ''' Watchdog event handler for the FileBase class that checks to see if the specified file was effected when
    something in the file's directory changes then passes the event to the user defined handlers in the FileBase
    class '''

    def __init__(self, fileToWatch):
        ''' Initiailise the event handler '''

        # Intialise the superclass and save a reference to the file object that we're watching
        super(FileBaseWatchDog, self).__init__()
        self.file = fileToWatch


    def on_moved(self, event):
        ''' Calls the files own event handler method (evt_OnFileMoved) that handles when a file is moved '''
        
        # Check that the file that was moved was the one we are watching
        if event.src_path == self.file.getAbsolutePath():
            self.file.evt_OnFileMoved(event)

    def on_deleted(self, event):
        ''' Calls the files own event handler method (evt_OnFileDeleted) that handles when a file is deleted '''

        # Check that the file that was deleted was the one we are watching
        if event.src_path == self.file.getAbsolutePath():
            self.file.evt_OnFileDeleted(event)

    def on_modified(self, event):
        ''' Calls the files own event handler method (evt_OnFileModified) that handles when a file is modified '''

        # Check that the file that was modified was the one we are watching
        if event.src_path == self.file.getAbsolutePath():
            self.file.evt_OnFileModified(event)


class FileBase(object):
    ''' Abstract base class that represents a file on disk. Tracks the state of the object and handles 
    pickling it so it can be saved to disk. An appropriate superclass of this would implement the GUI 
    functionality and specify the extra attributes and methods used to make the file useful '''

    def __init__(self, path=None):
        ''' If called with no arguments this initialises the object as an unsaved file with no directory 
        and no name, prompting a saveAs when save is first called. If a path is given this will load the 
        object from disk and mark it as unchanged '''
        
        # Variable to track unsaved changes
        self.unsavedChanges = False
        self.watchdog = None

        # Placeholders for the details of the file on disk
        self.name = None
        self.extension = None
        self.directory = None

        # Placeholder for the python object stored within the file
        self.data = None

        # If we were given a path then open that file
        if path is not None:
            
            # If the file exists then open it
            if os.path.exists(path):
                self.open(path)
            
            # Otherwise create the file
            else:
                self.saveAs(path)


    # ---------------------------------------------------------------------------------------------------
    # PRIVATE METHODS
    # ---------------------------------------------------------------------------------------------------

    def _throwNotEnoughInfo(itemThatFailed):
        ''' Throws a "NotEnoughInfoOnFile" exception about the given item (usually the watchdog or save operation)
        that failed because there wasn't enough information about the path, extension and/or filename '''
        
        # Create the error string based on what is missing
        errorString = "The file "
        errors = 0
        if self.name is None:
            errorString += "name"
            errors += 1
        if self.extension is None:
            errorString += " and extension" if errors > 0 else "extension"
            errors += 1
        if self.directory is None:
            errorString += " and directory" if errors > 0 else "directory"
            errors += 1
        
        # Add the item to the error string
        errorString += " to intialise the %s" % itemThatFailed

        # Raise an exception
        raise NotEnoughInfoOnFile(errorString)

    def _initWatchdog(self):
        ''' Intialises a watchdog thread to keep an eye on the file on disc to check if it is renamed, moved or
        deleted '''

        # Check we have a filename, extension and directory so we know what to watch
        if self.name is not None and self.extension is not None and self.directory is not None:
            
            # Create the watchdog and handler
            self.watchdog = watchdog.observers.Observer()
            self.watchdogHandler = FileBaseWatchDog(self)

            # Schedule the handler
            self.watchdog.schedule(self.watchdogHandler, path=self.directory, recursive=False)
            self.watchdog.start()
        
        else:
            # Figure out what was missing and construct a useful error message
            self._throwNotEnoughInfo("watchdog")

    def _updateFileLocation(self, path):
        ''' Updates the path of the file and restarts a new watchdog '''
        self._getInfoFromPath(path)
        self._initWatchdog()

    def _getInfoFromPath(self, path):
        ''' Given an absolute path to a file, this will save the directory, filename and extension of the file '''

        # Get the directory, filename and extension     
        self.directory = os.path.dirname(path)
        fileName = os.path.basename(path)
        self.name = fileName.split(".")[0]
        self.extension = os.path.splitext(path)[1]

    def _changesMade(self):
        ''' Sets the unsavedChanges flag to True so we know the version in memory is different from the ones on disc '''
        self.unsavedChanges = True


    # ---------------------------------------------------------------------------------------------------
    # EVENT HANDLERS
    # ---------------------------------------------------------------------------------------------------

    def evt_OnFileModified(self, event):
        ''' Update filename and / or path '''
        self._updateFileLocation(event.src_path)
        
    def evt_OnFileDeleted(self, event):
        ''' Prompt user about delete, if they are listening to catch this exception there is the option to use
        the recoverFromDelete method to specify a new file, otherwise next time this file is saved a new copy
        with the same filename and extension will be saved in the same location '''
        errorString = "The file %s was either deleted or moved from %s" % (self.name + self.extension, self.directory)
        raise FileDeleted(errorString)

    def evt_OnFileMoved(self, event):
        ''' Update directory value '''
        self._updateFileLocation(event.dest_path)


    # ---------------------------------------------------------------------------------------------------
    # PUBLIC METHODS
    # ---------------------------------------------------------------------------------------------------

    def hasUnsavedChanges(self):
        ''' Returns True if the object has changed since it was last opened or saved, otherwise False '''
        return self.unsavedChanges
    

    def open(self, path):
        ''' Opens the file from the given directory and saves the extension, filename and path. Also
        creates the watchdog object which handles things when the file changes on disk '''

        # Get the directory, filename and extension     
        self._getInfoFromPath(path)

        # Unpickle the data and load it to the object pointer
        with open(path, 'r+b') as f:
            self.data = pickle.load(f)

        # Now setup the watchdog for the file to check if things change on disc that we should know about
        self._initWatchdog()

    def save(self):
        ''' Saves the current file to disc, throws an exception if there isn't enough info internally about
        where to save the file and what name it should have '''

        # Check we have a filename, extension and directory so we know what to save our file as
        if self.name is not None and self.extension is not None and self.directory is not None:
            

            # Check if the file exists, if it doesn't create it
            path = self.getAbsolutePath()
            
            # Pickle the data and save the file
            with open(path, 'w+b') as f:
                pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
                f.close()
        
            # Mark that all changes are saved
            self.unsavedChanges = False

        else:
            # Figure out what was missing and construct a useful error message
            self._throwNotEnoughInfo("save")

    def saveAs(self, path):
        ''' Gets the new filename, extension and path from the given absolute path then saves the file. '''
        
        # Get the new save location, save the file then update the watchdog
        self._getInfoFromPath(path)
        self.save()
        self._initWatchdog()

    def getAbsolutePath(self):
        ''' Returns the absolute path of the file on disc '''
        return os.path.join(self.directory, self.name + self.extension)

    @makesChanges
    def setData(self, data):
        ''' Sets the data object associated with the file '''
        self.data = data

    def getData(self):
        ''' Returns the data associated with the file '''
        return self.data

    def recoverFromDelete(self, newPath):
        ''' Called to point the file object to a new file when a delete happens to stop things from exploding '''
        self._updateFileLocation(newPath)


# --------------------------------------------------------------------------------------------------------------------
# DEMO
# --------------------------------------------------------------------------------------------------------------------        

if __name__ == "__main__":

    # Create a bogus file
    # path = "PUT THE ABSOLUTE PATH TO A FILE HERE, INCULDING THE FILE NAME AND EXTENTION (IT DOE'SNT HAVE TO EXIST)"
    path = "/Users/ashokfernandez/Software/WesternEnergy/Foo.bar"
    myFile = FileBase(path)

    # Print that the data isn't changed, change the data then show that the changes were tracked
    print "It is %s that there is unsaved changes in this file" % myFile.hasUnsavedChanges()
    print "Adding some data to the file"
    myFile.setData("SOME BOGUS DATA")
    print "Now it is %s that there is unsaved changes in this file" % myFile.hasUnsavedChanges() 

    # Lets save the changes
    print "Saving file..."
    myFile.save()
    print "Now it is %s that there is unsaved changes in this file" % myFile.hasUnsavedChanges() 

    # Now loop and watch the file system, feel free to rename or delete the file and see what happens
    print "Entering infinite loop to demostrate watchdog, press CTRL+C to exit"
    print "Feel free to rename or delete the file and see what happens..."
    
    import time

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print "\nClosing file demo, goodbye!" 