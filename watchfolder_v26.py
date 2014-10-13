# watchfolder.py looks at folder and transcodes every .mov file to
# .mp4 and .wmv acroding to the length and resolution
# The new files are created acording to a set of pre-configured presets, 
# Last update - 2013-08-08
# determing the resolution and length of the .mov.
# Files that are not 16:9 or 4:3 will not be converted.

# Running the file from command line will crawl a folder (path_to_watch) every X seconds (crawl_interval).
# If the .mov file is older than Y seconds (safty_seconds), relevant .mp4 and .wmv files will be created in (path_to_export)

# If you wish to exclude a path or project from being transcoded, you can specify a string in the exclude_list. 

# Dependencies:
# This Python script was written and tested on Python version 3.3.2.
# Information about the MOV files is acquired via MediaInfo_CLI.
#	Version 0.7.64, 2013-07-05 was used. No need to install, only direct to MediaInfo.exe.
# 	http://mediaarea.net/he/MediaInfo/Download/Windows
# WMV transcode requires intalling Windows Media Encoder 9 Series. 
# 	The file is WMEncoder.exe that can be found at http://www.microsoft.com/en-us/download/details.aspx?id=17792 .
#	Acces to the encoder is done via WMCmd.vbs script which runs through the cscript windows command. 
#	Note that the x68 version of the script is needed for this to work.
# MP4 x264 transcodes using FFmpeg. There's no need for install, only to direct the script to ffmpeg.exe
# 	Version used is 2013-07-13 git-aac57c7 - http://ffmpeg.zeranoe.com/builds/

import os, time, datetime, subprocess, shutil

# SCRIPT CONFIGURATION START

# Set one of these modes. The rest must be commented out.
# Only test mode transcodes the files after the initial crawl. The rest only transcodes new files added after initial crawl.
mode = "test"
#mode = "drafts"
#mode = "folder1"

# path_to_watch defines path to watch as a string with exeprions. All slashes must be doubled.
# path_to_export defines path to export the files to as a string with exeprions. All slashes must be doubled.
# path_of_temp defines path to export the files to as a string with exeprions. All slashes must be doubled.
if mode == "test" :
	path_to_watch = "D:\\Noam\\watchfolder\\testing\\in"
	path_to_export = "D:\\Noam\\watchfolder\\testing\\out"
	path_of_temp = "D:\\Noam\\watchfolder\\testing\\temp"

elif mode == "drafts" :
	path_to_watch = "\\\\watch1\\drafts"
	path_to_export = "D:\\watchfolder\\transcoded\\drafts_transcoded"
	path_of_temp = "D:\\watchfolder\\temp_files\\drafts"

elif mode == "masters" :
	path_to_watch = "\\\\watch1\\masters"
	path_to_export = "D:\\watchfolder\\transcoded\\masters_transcoded"
	path_of_temp = "D:\\watchfolder\\temp_files\\masters"

# FFmpeg and MediaInfoCLI location
if mode == "test" :
	ffmpeg_location = "D:\\Noam\\watchfolder\\software\\ffmpeg\\bin\\ffmpeg.exe"
	WMCmd_location = '"C:\\Windows\\SysWOW64\\cscript" "D:\\Noam\\watchfolder\\software\\WMCmd\\WMCmd.vbs"'
	mediaInfoCLI_location = "D:\\Noam\\watchfolder\\software\\MediaInfo_CLI\\MediaInfo.exe"

elif mode == "drafts" :
	ffmpeg_location = "D:\\watchfolder\\software\\ffmpeg\\bin\\ffmpeg.exe"
	WMCmd_location = '"C:\\Windows\\SysWOW64\\cscript" "D:\\watchfolder\\software\\WMCmd\\WMCmd.vbs"'
	mediaInfoCLI_location = "D:\\watchfolder\\software\\MediaInfo_CLI\\MediaInfo.exe"

elif mode == "masters" :
	ffmpeg_location = "D:\\watchfolder\\software\\ffmpeg\\bin\\ffmpeg.exe"
	WMCmd_location = '"C:\\Windows\\SysWOW64\\cscript" "D:\\watchfolder\\software\\WMCmd\\WMCmd.vbs"'
	mediaInfoCLI_location = "D:\\watchfolder\\software\\MediaInfo_CLI\\MediaInfo.exe"

# Crawl interval, in seconds as integer
if mode == "test" :
	crawl_interval = 15
else:
	crawl_interval = 60

# Safty margine time for complete file, in seconds as integer
safty_seconds = 180

# Exclude_list is a list of string that should not appear in the path or name of files to convert.
# This prevents items on folders such as "temp_masters" and "Anamorphic" to be excluded from the list Added. 
# The strings are case senetive.
exclude_list = [ "temp_masters", "Anamorphic", "anamorphic", "ANAMORPHIC", "Anamorfic", "anamorfic", "ANAMORFIC" ]


# If you want to add all the files for initial conversion, use:
if mode == "test" :
	before = {}

# If you want to just monitor changes without initial crawl, you must set
# before = list_current()
# in the actual program below. (the problem is no function can be called before declared)

# The following ffmpeg presets are arguments for ffmpeg and WMCmd. 
# mp4 files are created in ffmpeg. wmv files are created in WMCmd since ffmpeg has no support for WMV9 or WVC1.
# ffmpeg arguments:
# -loglevel fatal == ffmpeg will only write something if it comes across a fatal error. see ffmpeg for other options.
# -c:v == codec of the video. libx264 is for x264 and msmpeg4v3 is wmv 8.
# -pix_fmt yuv420p == use 4:2:0 chroma subsampling.
# -b:v == video bitrate
# -aspect == make sure the screen aspect ratio is correct. it forces ffmpeg to disregard anamorphic video, and export it as regular 4:3 content.
# -ac 1 == have 1 audio channel.
# -ar 44100 == 44.1 khz audio sampling
# -ab == audio bitrate
# -s == scale
# -r == Frame rate
# -y == overwrite the file if in current directory
#
# WMCmd arguments:
# -silent == Minimises the textual output of WMCmd. Unfortunatly there's nothing lower than this.
# -v_codec WVC1 == Sets the video codec to WVC1.
# -v_width , -v_height == Width, Hight.
# -v_framerate == Framerate. Note that for some unknown readon, Windows identifies the FPS as 30. this happens in both ffmpeg and WMCmd.
# -v_bitrate == The desired bitrate. The overhead in wmv files is much bigger than in mp4 so in order to achieve the 5MB limit deduction is preformed.
# -v_quality == CBR: Quality/smoothness tradeoff. 0 to 100, 0 being the smoothest. Higher values might drop frames in order to maintain image quality.
# -pixelformat I420 == Sets 4:2:0 chroma subsampling.
# -a_codec WMAPRO == Sets the audio codec.
# -a_setting 96_44_2_16 == These are actualy four audio variables meshed into one. Audio bitreate 96kbps, 44.1khz sampling rate, 2 chanels (no option for mono), 16bit bit depth.
# For more arguments see http://alexzambelli.com/WMV/WMCmd.txt 
transcode_presets = {	# presets for mp4, aspect ratio 16:9 (1.778)
					"mp4 smaller than 34s 1024x576": " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 1200k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 1024x576 -r 25 -y ",
					"mp4 smaller than 50s 640x360":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 800k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 640x360 -r 25 -y ",
					"mp4 smaller than 71s 640x360":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 500k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 640x360 -r 25 -y ",
					"mp4 greater than 71s 1024x576": " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 2000k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 1024x576 -r 25 -y ",
					
					# presets for mp4, aspect ratio 4:3 (1.333)
					"mp4 smaller than 34s 720x576":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 1200k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 720x576 -r 25 -y ",
					"mp4 smaller than 50s 640x480":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 800k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 640x480 -r 25 -y ",
					"mp4 smaller than 71s 640x480":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 500k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 640x480 -r 25 -y ",
					"mp4 greater than 71s 720x576":  " -loglevel fatal -c:v libx264 -pix_fmt yuv420p -b:v 2000k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 720x576 -r 25 -y ",
					
					# The following presets use WMcmd's problematic wmv encode.
					# presets for wmv, aspect ratio 16:9 (1.778)
					#"wmv smaller than 34s 1024x576": " -silent -v_codec WVC1 -v_width 1024 -v_height 576 -v_framerate 25 -v_bitrate 1050000 -v_quality 95 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv smaller than 50s 640x360":  " -silent -v_codec WVC1 -v_width 640 -v_height 360 -v_framerate 25 -v_bitrate 700000 -v_quality 90 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv smaller than 71s 640x360":  " -silent -v_codec WVC1 -v_width 640 -v_height 360 -v_framerate 25 -v_bitrate 450000 -v_quality 85 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv greater than 71s 1024x576": " -silent -v_codec WVC1 -v_width 1024 -v_height 576 -v_framerate 25 -v_bitrate 2000000 -v_quality 95 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					
					# presets for wmv, aspect ratio 4:3 (1.333)
					#"wmv smaller than 34s 720x576":  " -silent -v_codec WVC1 -v_width 720 -v_height 576 -v_framerate 25 -v_bitrate 1050000 -v_quality 95 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv smaller than 50s 640x480":  " -silent -v_codec WVC1 -v_width 640 -v_height 480 -v_framerate 25 -v_bitrate 700000 -v_quality 90 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv smaller than 71s 640x480":  " -silent -v_codec WVC1 -v_width 640 -v_height 480 -v_framerate 25 -v_bitrate 450000 -v_quality 85 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output ",
					#"wmv greater than 71s 720x576":  " -silent -v_codec WVC1 -v_width 720 -v_height 576 -v_framerate 25 -v_bitrate 2000000 -v_quality 95 -pixelformat I420 -a_codec WMAPRO -a_setting 96_44_2_16 -output " 
					
					# The following presets use ffmpeg's low quality wmv encode.
					#OLD presets for wmv, aspect ratio 16:9 (1.778)
					"wmv smaller than 34s 1024x576": " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 1200k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 1024x576 -r 25 -y ",
					"wmv smaller than 50s 640x360":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 800k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 640x360 -r 25 -y ",
					"wmv smaller than 71s 640x360":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 500k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 640x360 -r 25 -y ",
					"wmv greater than 71s 1024x576": " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 2000k -aspect 16:9 -ac 1 -ar 44100 -ab 96k -s 1024x576 -r 25 -y ",
					
					#OLD presets for wmv, aspect ratio 4:3 (1.333)
					"wmv smaller than 34s 720x576":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 1200k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 720x576 -r 25 -y ",
					"wmv smaller than 50s 640x480":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 800k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 640x480 -r 25 -y ",
					"wmv smaller than 71s 640x480":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 500k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 640x480 -r 25 -y ",
					"wmv greater than 71s 720x576":  " -loglevel fatal -c:v msmpeg4v3 -pix_fmt yuv420p -b:v 2000k -aspect 4:3 -ac 1 -ar 44100 -ab 96k -s 720x576 -r 25 -y " 
					
					}

# SCRIPT CONFIGURATION END



# Modification_date recives a filename and returns the modification date in human readable manner
# eg. yyyy-mm-dd hh:mm:ss.miliseconds
def modification_date(filename):
	t = os.path.getmtime(filename)
	return datetime.datetime.fromtimestamp(t)

	
# Trim_added removes files from added if they have one of the strings in exclude_list.
def trim_added(added):
	# to_remove is used to store the files to remove as a list
	to_remove = []

	# This block goes over added and looks files (and their paths) which have one of the items in the exclude_list.
	# It then appends the name to the to_remove list
	for place in range(len(added)):
		for exclude in exclude_list:
			if exclude in added[place]:
				to_remove.append(added[place])

	# trims if a file is on to_remove it wil be removed from added.
	added = list(set(added)-set(to_remove))
	return added


# list_current crawls through the subfolders in selected path 
# and outputs the .mov files as a dictionary with exeptions of files that are smaller than 1Mbit or still open on an other machine.
def list_current():
	after = {}
	# Crawl directory.
	for path, subdirs, files in os.walk(path_to_watch):
		for name in files:
			current_file_name = os.path.join(path, name)
			
			# Conditional - if file is .mov and it's size is bigger than 1000000 bits (1Mb is less than an uncompresed SD frame) 
			# 	and hasn't been modified in X seconds, x defined by safty_seconds above do:
			if name.endswith(".mov") and os.path.getsize(current_file_name) > 1000000\
				and (round(float(os.path.getmtime(os.path.join(path, name)))) + safty_seconds ) < round(time.time()):
				# after's structure uses the timestamp (in miliseconds) as key and the path as value.
				after[str(round(float(os.path.getmtime(current_file_name))))] = current_file_name

	return after


# get_mov_info(place) recives place, and integer uses it to know which location in added to get the info on.
# the function returns the aspect ratio as float with three digits after the decimal point and the duration in seconds as integer.
def get_mov_info(place): 

	# Concats the command from MediaInfoCLI location, the command operators and the relevant filename
	aspect_ratio_command = str(mediaInfoCLI_location) + " --Output=Video;%Width%---%Height%---%Duration% " + '"' + str(added[place] + '"')

	# These two lines capture the output (in stdout) of the command. 
	p = subprocess.Popen(aspect_ratio_command, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	stdout_text = p.stdout.read()
	
	# Stripping junk from stdout_text and puts it into variables.
	info = (str(stdout_text.rstrip())[2:-1])
	width = info.split("---")[0]
	height = info.split("---")[1]
	duration = int(info.split("---")[2][:-3])

	# Anamorphic video appears as is 703 px wide, has 1.093 pixel aspect ratio so the overall ratio is 1.333 as it should be.
	# However, this conflicts with our results of having 1.25 (=720/576, PAR 1:1). 768 is the result of 576*1.333 .
	if width == "703" or width == "720" and height == "576":
		width = "768"
	aspect_ratio = round(int(width) / int(height), 3)

	return aspect_ratio, duration
	

# The function encode recives the current added array, the place to operate on, and two presets to use.
# It will create the relevant sub-directories in path_to_export as configured above and then .mp4 and .wmv files. 
# Textual message success or failure messages will be printed.
def encode(added, place, preset_mp4, preset_wmv): 
	
	# Extracts the filename from the complete path.
	name = added[place].rsplit("\\", 1)[1]

	# Prepares the temp filenames.
	temp_dir_and_name = path_of_temp + added[place][len(path_to_watch):]
	temp_dir_and_name_mp4 = temp_dir_and_name.rsplit(".mo", 1)[0] + ".mp4"
	temp_dir_and_name_wmv = temp_dir_and_name.rsplit(".mo", 1)[0] + ".wmv"
	
	# Prepares the final filenames - the place there the files will be at the end.
	new_dir_and_name = path_to_export + added[place][len(path_to_watch):]
	new_dir_and_name_mp4 = new_dir_and_name.rsplit(".mo", 1)[0] + ".mp4"
	new_dir_and_name_wmv = new_dir_and_name.rsplit(".mo", 1)[0] + ".wmv"
	
	# If there's no temp folder to output, these lines create it.
	temp_dir = temp_dir_and_name.rsplit("\\", 1)[0]
	if not os.path.exists(temp_dir):
		os.makedirs(temp_dir)
	
	# Copy the file to the temp directory.
	print ("Copying " + name + " to temp dir " + temp_dir + " ...")
	shutil.copy2(added[place], temp_dir)
	
	# Generates and calls the ffmpeg and WMCmd commands. -i stands for input. All paths must be in qoutes or a space in the path will cause undesired results.
	mp4_command = str(ffmpeg_location) + " -i " + '"' + temp_dir_and_name + '"' + transcode_presets[preset_mp4] + '"' + str(temp_dir_and_name_mp4) + '"'
	subprocess.call(mp4_command)
	wmv_command = str(ffmpeg_location) + " -i " + '"' + temp_dir_and_name + '"' + transcode_presets[preset_wmv] + '"' + str(temp_dir_and_name_wmv) + '"'
	subprocess.call(wmv_command)

	# Makes sure the file exists and the prints a message about the name, location and preset used.
	# If the file wasn't created for some reason, an error is printed.

	# If there's no folder to output, these lines create it.
	new_dir = new_dir_and_name.rsplit("\\", 1)[0]
	if not os.path.exists(new_dir):
		os.makedirs(new_dir)

	# Copy the new mp4 and wmv to the output directory.	
	shutil.copy2(temp_dir_and_name_mp4, new_dir)
	shutil.copy2(temp_dir_and_name_wmv, new_dir)

	if os.path.exists(new_dir_and_name_mp4):
		print (new_dir_and_name_mp4)
		print ("was created in folder " + new_dir + " using the preset - " + preset_mp4)
	else:
		print (new_dir_and_name_mp4 + " WASN'T CREATED.")
	
	if os.path.exists(new_dir_and_name_wmv):
		print (new_dir_and_name_wmv)
		print ("was created in folder " + new_dir + " using the preset - " + preset_wmv)
	else:
		print (new_dir_and_name_wmv + " WASN'T CREATED.")

	# Removes the temp file and verifies it's gone. If not, prints a message.
	os.remove(temp_dir_and_name)
	if os.path.exists(temp_dir_and_name):
		print ("Temporary file " + temp_dir_and_name + " WASN'T DELETED.")

	print ("")
	return None




# PART OF CONFIG
# This is used if you want the first run to be empty and only transcode new stuff.
if mode != "test" :
	before = list_current()

if __name__ == "__main__":
	while True:
		print (" ")
		
		# Check for changes since last time
		after = list_current()
		
		# These lines makes added the added difference between before and after, stored in a list.
		# Almost all operations from here on end will use added alone.
		added = []
		for key in after:
			added = [after[key] for key in after if not key in before]
		
		added = trim_added(added)
		# This if block prints added one value per line.
		if added: 
			print ('Added has', len(added), "items:")
			for key in added:
				print (key)
			print ("")

			# This If block calls to encode function according to the aspect ratio and duration of each file.
			# The presets are designed to create the best looking mp4 and wmv files possible for under 5 MB, including a 10% margin of error.
			# If the file is longer then 71 seconds it's probably not a standart commercial but a corporate video or music video
			# and therefore will be created at a higher bitrate, as specified by the presets.
			# If the aspect ratio is not 1.778 or 1.333 the file will not be converted. 
			for place in range(len(added)):
				
				# get_mov_info() may raise IndexError and ValueError exeptions if the file is not a proper video file with width, height and duration parameters.
				# Therefore, a try was set to catch the exception.
				if added:
					working_file = added[place]
				try:
					aspect_ratio, duration = get_mov_info(place)
				# What to do if getting an exeption -
				except IndexError:
					working_file = added[place]
					print (str(working_file) + "\nis not a valid video file. If this problem consist, check the file.")
					
					# Removing the file from the after so it will be re-added next time.
					print ("Removing " + working_file + " from queue!")
					for key, item in after.items():
						if item is working_file:
							exit
					del after[key]
					continue
				
				if aspect_ratio == 1.778:
					if duration < 33:
						encode(added, place, "mp4 smaller than 34s 1024x576", "wmv smaller than 34s 1024x576")
					elif duration < 50:
						encode(added, place, "mp4 smaller than 50s 640x360", "wmv smaller than 50s 640x360")
					elif duration < 71:
						encode(added, place, "mp4 smaller than 71s 640x360", "wmv smaller than 71s 640x360")
					else: #for reverything larger than 70 seconds
						encode(added, place, "mp4 greater than 71s 1024x576", "wmv greater than 71s 1024x576")
				
				elif aspect_ratio == 1.333:
					if duration < 33:
						encode(added, place, "mp4 smaller than 34s 720x576", "wmv smaller than 34s 720x576")
					elif duration < 50:
						encode(added, place, "mp4 smaller than 50s 640x480", "wmv smaller than 50s 640x480")
					elif duration < 71:
						encode(added, place, "mp4 smaller than 71s 640x480", "wmv smaller than 71s 640x480")
					else: #for reverything larger than 70 seconds
						encode(added, place, "mp4 greater than 71s 720x576", "wmv greater than 71s 720x576")

				else:
					print (str(working_file.rsplit("\\", 1)[1]) + " doesn't have aspect ratio of 1.778 or 1.333 .")
				
		# If there's no new files in added, these three lines apear every cycle.
		# They off the user info on the path crawled, the time of the last crawl cycle, crawl interval and how to stop the crawl.
		else:
			print ("No new relevant files in " + path_to_watch)
			print (str(datetime.datetime.fromtimestamp(time.time())) + " Cheking every " + str(crawl_interval) + " seconds for new files. The mode is '" + mode + "'.")
			print ("Press Ctrl + c or close terminal to terminate crawl.")

		# Makes before equal to after in order to compare what was already in the folders and what's new.
		before = after

		# Time to wait, in seconds, before the cycle starts again. 
		time.sleep(crawl_interval)

	