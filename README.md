Watchfolder
===========

Watchfolder automates the creation of video files using Python, FFmpeg, and MediaInfoCLI.
The program's goal is to create files smaller than 5 MB for client preview, while taking into considiration the length, resolution and aspect ratio to adapt relative resolution and bitrate to fit constrains. It's best used for TV spots.

There's no installation required other than Python 3. Configuration is done in the file.

Please see further documentation in the file.

Key features:
- Activly scans input folder for new video file.
- Transcode files by defined presets.
- Exclude list ignores files with set strings.
- Overwrites old files.
- Supports all CLI transcoders (WMCmd works on some machines)

Known bugs:
- Program crashes then trying to overwrite a video file without write priviliges (usualy when the file is open somewhere).


License:
The MIT License (MIT)