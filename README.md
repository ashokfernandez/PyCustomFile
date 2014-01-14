# PyCustomFile
### Allows easy creation of custom files in Python by handling low level file operations


## Author
[Ashok Fernandez](https://github.com/ashokfernandez/)


## Description: 
Extending FileBase allows the user to create a custom filetype without worrying about low-level file operations and tracking changes that have happened on disc.

Custom files are saved on disc with any given extension and can carry any python data with them by using the setData method. The data stored using this method is pickled and saved in the file. 

Methods that are decorated with the @makesChanges decorator will set a flag that automatically tracks when the file has been changed from what it was on disc. For example

    @makesChanges
    def doSomething(self, thing):
        self.something = thing

Will make hasUnsavedChanges return true after doSomething has been called.

If higher level methods only change the files data object using the setData method then all changes to the files python data object will be tracked as setData is decorated with @makesChanges.

## Usage example: 
See bottom of PyCustomFile.py