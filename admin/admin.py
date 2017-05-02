#! /usr/bin/env python2.7
import crypt

'''
Authentication module for admin.

DESCRIPTION
===========

This module  authenticate the user based on username and a password.

FILES
=====

``.password.txt`` where password are stored in the parent directory. The
password follows unix philosophy.


'''

def authUser(username, password):
    """
    This function read password from ``.password.txt`` and  checks if the
    provided username and password if matched.

    Returns:
        bool: True if successful, False otherwise.
    """

    passFile = open(".password.txt")

    for line in passFile.readlines():
        if ":" in line:
            user = line.split(':')[0]  # username
            cryptPass = line.split(':')[1].strip(' ' + '\n')# password 
            salt = cryptPass[0:5]
            cryptWord = crypt.crypt(password, salt)
            # Check if the username exist in the file
            if username == user:
                # Check if password matches
                if(cryptPass == cryptWord):
                    return True
                else:
                    return False
            else:
                return False
