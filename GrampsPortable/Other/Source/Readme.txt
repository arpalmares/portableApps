Gramps Portable Launcher
=========================
Copyright 2004-2015 John T. Haller
Copyright 2008-2015 Bart.S

Website: http://PortableApps.com/GrampsPortable

This software is OSI Certified Open Source Software.
OSI Certified is a certification mark of the Open Source Initiative.

This program is free software; you can redistribute it and/or 
modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation; either version 2 
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, 
but WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
GNU General Public License for more details.

You should have received a copy of the GNU General Public License 
along with this program; if not, write to the Free Software 
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


ABOUT GRAMPS PORTABLE
======================
The Gramps Portable Launcher allows you to run Gramps from a removable drive whose 
letter changes as you move it to another computer. The program can be entirely self-
contained on the drive and then used on any Windows computer.


LICENSE
========
This code is released under the GPL. The source is included with this package as 
GrampsPortable.nsi.


INSTALLATION / DIRECTORY STRUCTURE
===================================
By default, the program expects the following directory structure:

-\ <--- Directory with GrampsPortable.exe
	+\App\
		+\Gramps\
		+\GTK\
		+\Python27\
	+\Data\
		+\settings\


It can be used in other directory configurations by including the GrampsPortable.ini 
file in the same directory as GrampsPortable.exe and configuring it as details in the 
INI file section below.


GRAMPSPORTABLE.INI CONFIGURATION
=================================
The Gramps Portable Launcher will look for an ini file called GrampsPortable.ini 
within its directory (see the Installation/Directory Structure section above for more 
details). If you are happy with the default options, it is not necessary, though. The 
INI file is formatted as follows:

[GrampsPortable]
GrampsDirectory=App\Gramps
GTKDirectory=App\GTK
PythonDirectory=App\Phyton27
SettingsDirectory=Data\settings
AdditionalParameters=
DisableSplashScreen=false
AllowMultipleInstances=false

The GrampsDirectory, GTKDirectory, PythonDirectory and SettingsDirectory entries should be 
set to the *relative* path to the appropriate directories from the current directory. They 
must be a subdirectory (or multiple subdirectories) of the directory containing GrampsPortable.exe. 
The default entries for these are described in the installation section above.

The AdditionalParameters entry allows you to pass additional commandline parameter entries to 
the GrampsExecutable. Whatever you enter here will be appended to the call to gramps.py.

The DisableSplashScreen entry allows you to run the Gramps Portable Launcher without the 
splash screen showing up. The default is false.

The AllowMultipleInstances entry allows you to run multiple instances of Gramps Portable. 
The default is false.

PROGRAM HISTORY / ABOUT THE AUTHORS
====================================
This launcher is written from scratch in NSIS. A previous package of Gramps Portable by 
Christian Lobenstein (www.ormus.info) made use of Delphi. 
