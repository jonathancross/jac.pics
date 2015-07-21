#!/usr/bin/perl
#
my $VERSION = '1.0.0';
#
# Jonathan Cross : www.JonathanCross.com : 2004-2012
# This script may be used free for any non-commercial purpose.
#
# JCDSee creates a user-customizable linked directory listing in HTML format.
# Will also generate and cache thumbnails of any GIF, JPEG or PNG images it finds.
# Also contains a sequential image viewer, slideshow and various navigation devices.
# Best viewed with IE6+ or Mozilla/Firefox 1.0+
#
# COMMANDLINE DEBUG PARAMS (YMMV):
#     [script-name] debug <directory> <display_mode> <pic_cur_idx>
#     All args in <> are optional.
#
# URl PARAMS (Everything is optional.  If no url is provided, the current location of the script is used):
#    index.cgi?pic=[full path to picture]&display_mode=[LIST|THUMBS|SINGLE|SLIDESHOW]&cur_url=[full path to folder]
#    Defaults: display_mode=LIST
#              cur_url=<current folder>
#
#    EXAMPLE URLs (assuming JCDSee is in the web root):
#     http://zzz.com/
#     http://zzz.com/jcdsee.cgi?cur_url=/pics/
#     http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg
#     http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg&display_mode=SLIDESHOW
#     http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg&display_mode=THUMBS
#    If you can use mod_rewrite then you can access folders like so:
#     http://zzz.com/pics/2/  (results in: http://zzz.com/jcdsee.cgi?cur_url=/pics/2/)
#
# FEATURES:
#   - Able to recognize 5 file types (image, folder, music, "text document" and "other")
#     "other" file types can include video, or anything else, but will not have an icon unless you provide one manually.
#   - Will generate & cache thumbnail icons of any jpeg, gif or png files it finds.
#   - 2 additional thumbnail resolutions.
#   - Optimized to only read / write necessary image information.
#   - 4 display modes ("list","thumbnail", "single image" and DHTML "slideshow").
#   - In "single" (full-size) image display mode, the script will pre-cache next and previous images in browser.
#   - Will maintain display settings across folders (assuming you only use the links on the page)
#   - Clean URLs
#   - Uses advanced page transitions in IE and CSS transparency in Mozilla.
#   - Adding a new folder of images just requires a unix "hard link" to the script and you are done!
#   - All "rollovers" are done with CSS transparency and A:hover pseudo-class (no messy javascript)
#
# JCDSEE ADMIN (admin script available upon request):
#   - Easily add new folders
#   - Write file / folder descriptions in browser
#   - Create google sitemap.xml file.
#   - Various backup, cleaning and undo tasks.
#   - Even re-program JCDSee or the admin script itself!
#
# BUGS:
#   - pic parameter needs to handle trailing slashes and non-existant files better?
#   - broken image name in database just stops processing the list.
#   - thumbs in SINGLE mode loose transparency after full is loaded.
#   - FIXED: UTF-8 chars get munged...
#   - FIXED: Cool CSS hover effect only works in Mozilla right now.
#   - FIXED: 'filter'  /jcdsee/jcdsee.css  Line: 52
#
# WISHLIST / FIXES:
#  - rss, remove all file system IO, REAL video & audio support and inline player.
#    re-write in php, search, more robust slideshow with thumbs.
#    mpeg video: http://fresh.t-systems-sfr.com/unix/src/misc/mpeg2vidcodec_v12.tar.gz/
#    PSD icons: complex to flatten...
#    convert databases to xml and allow in-browser editing of descriptions.
#    non-destructive folder "refresh" when files are added or removed. (part-way ther 2010 with listing in admin console)
#    COMPLETED:
#      global database (2008-02-01).
#      404 Error page (2008-03-01).
#      Got rid of usage.cgi - re-write in perl
#      dir descriptions at top of page
#      thumb mode = remove #_ prefix just like list (2010-07-27) v1.8.5
#      Fixed thumb display in webkit browsers (2010-07-27) v1.8.5
#      Consistent thumb height (2012-01-02) v1.8.9
#      Basic Commandline thumb generation fixed (2012-01-04) v1.9.1
#      Fixed thumb mode: filenames with periods, update admin button (2012-01-05) v1.9.2
#
# =========================================================================
use strict;
use Image::Magick;
use CGI ':standard';
use CGI::Carp 'fatalsToBrowser'; 
use Fcntl ':mode';
use Time::HiRes 'gettimeofday';
use XML::LibXSLT;
use XML::LibXML;

my %TIMER;
$TIMER{'total_s'}=gettimeofday();
# Allow commandline execution / debugging
my ${COMMANDLINE} = 0;
if ( defined($ARGV[0]) && ($ARGV[0] eq "debug") ) {
  ${COMMANDLINE} = 1;
  print "\nDEBUG MODE - Version: $VERSION\n\n";
}

# GLOBAL VARIABLES ==================================================================================================
# DIRECTORY LIST ARRAYS
my(@dir_list, @image_array, %image_hash, %file_descriptions, %file_types);
my ${tmp};
my ${DUMP} = '';
my ${ERROR} = 0;
my ${country_code} = (${COMMANDLINE}) ? 'none' : $ENV{'HTTP_CF_IPCOUNTRY'};
my ${root} = (${COMMANDLINE}) ? '.' : $ENV{DOCUMENT_ROOT};
my ${pic_root} = '/pics';
my ${assets_root} = '/jcdsee'; #folder containing assets used by this script. (icons, buttons, css, etc)
my ${script_name} = 'jcdsee.cgi'; #Name of the stub script, we need this so we don't show it in the dir listing.
my ${script_url}  = "/${script_name}"; # The main script URL used by links.  Because we name it "index.cgi", we can just use a question mapk after folder name.  This one is always used unless user hits a folder directly.
my ${test_url}    = "test"; # Special test mode staging url
my ${title_char} = ' : ';
my $amp='&amp;';
# XML / XSL objects
my $XMLparser = XML::LibXML->new();
my $xslt = XML::LibXSLT->new();
my $xml_sitemap_file = "${root}/sitemap.xml";
my $xsl_file = "${root}${assets_root}/jcdsee.xsl";
if (! -f $xml_sitemap_file) { return "lost XML: $xml_sitemap_file"; }
if (! -f $xsl_file) { return "lost xsl: $xsl_file"; }
my $sitemap = $XMLparser->parse_file($xml_sitemap_file);
my $style_doc = $XMLparser->parse_file($xsl_file);
my $stylesheet = $xslt->parse_stylesheet($style_doc);
# ONE STEP
# my $stylesheet = $xslt->parse_stylesheet_file($xsl_file);


# CONSTANTS FOR IMAGE PROCESSING
my %IMAGE_GLOBAL = (
  thumb_quality => 80,     #Thumbnail jpeg quality
  max_width_small => 50,   #Max width of small thumbs
  max_width_large => 400,  #Max width of large thumbs
  max_height_small => 50,   #Max height of small thumbs
  max_height_large => 140,  #Max height of large thumbs
  prefix_small  => '.S.',  #File name prefix to use for Small generated thumbnail images
  prefix_large  => '.L.',  #File name prefix to use for Large generated thumbnail images
  thumb_ext     => '.jpg' #File extension of generated thumbnail images
);

# VARS FOR CURRENT IMAGE PROCESSING STATE, PERHAPS SHOULD BE MOVED TO %STATE ?
my %IMAGE = (
  max_width     => 0,      #Max width placeholder
  max_height    => 0       #Max height placeholder
);

#DISPLAY STATE VARS
my %STATE = (
  dir               => '', # Full server path to the folder being listed.
  url               => '', # The path from the webserver document root.
  url_encoded       => '', # The path from the webserver document root. (URL encoded)
  title             => 'Jonathan Cross', # Document title base
  cur_dir_name      => '', # Will have only the name of the current directory (no slashes)
  display_mode      => '', # Display mode (SINGLE|LIST|THUMBS|SLIDESHOW) Default=LIST
  test_mode         => 0,  # Test mode (0 or 1) Default=0
  page_description  => '', # Description of current page (from xml database)
  prefix_cur        => '', # Will hold the current prefix (prefix_small or prefix_large)
  thumb_ext_cur     => '', # Will hold the current extension (thumbnail pics are always jpg for example)
  is_default        => 1,  # A boolean to tell us if all the display settings are at default.
  # VARS below used for current position in photo list
  pic_last_idx      => 0,
  pic_array_length  => 0,
  pic_cur_idx       => 0,
  pic_next_idx      => 0,
  pic_previous_idx  => 0,
  pic_cur_number    => 0,
  pic_previous_file => '',
  pic_cur_file      => '',
  pic_next_file     => '',
);
my %DEFAULTS = (
  display_mode      => 'LIST',
  test_mode         => 0,
);

# LOAD / SET PARAMS & DEFAULTS
$STATE{'display_mode'} = param('display_mode');
$STATE{'pic_cur_file'} = (param('pic_cur_file'))? param('pic_cur_file') : '';
#Make sure pic_cur_idx is a normal number, otherwise set to 0
$STATE{'pic_cur_idx'} = ( param('pic_cur_idx') =~ /^[0-9]+$/ ) ? int(param('pic_cur_idx')) : 0;
$STATE{'test_mode'} = ( $ENV{SERVER_NAME} =~ /^$test_url/ ) ? 1 : 0;

# CURRENT URL FROM PARAM -OR- PATH
if (param('cur_url')) {
  $STATE{'url'} = param('cur_url');
  $STATE{'url'} =~ s:[^/]$:$&/:;
  $STATE{'display_mode'} = ($STATE{'display_mode'})? $STATE{'display_mode'} : 'LIST';
} elsif (param('pic') && (param('pic') =~ m:(.*/)(.*):) ) {
  #get folder url from the pic param
  $STATE{'url'} = $1;
  $STATE{'pic_cur_file'} = $2;
  $STATE{'display_mode'} = ($STATE{'display_mode'})? $STATE{'display_mode'} : 'SINGLE';
} else {
  $STATE{'url'} = $ENV{REQUEST_URI};
  $STATE{'url'} =~ s/%20/ /g;
  $STATE{'display_mode'} = ($STATE{'display_mode'})? $STATE{'display_mode'} : 'LIST';
}
if (${COMMANDLINE}) {
  $STATE{'url'} = (${ARGV[1]}) ? ${ARGV[1]} : "${root}${pic_root}"; # HAVE DIR DEFAULT TO "." FOR COMMANDLINE DEBUGGING
  $STATE{'dir'} = $STATE{'url'};
  $STATE{'display_mode'} = ${ARGV[2]};
  $STATE{'pic_cur_idx'} = int(${ARGV[3]});
} elsif ($STATE{'url'} =~ m:^/: && $STATE{'url'} !~ m:/[.][.]: && -d $ENV{DOCUMENT_ROOT}.$STATE{'url'}){ # Have to validate the directory for security reasons
  $STATE{'dir'} = $ENV{DOCUMENT_ROOT}.$STATE{'url'};
  $STATE{'cur_dir_name'} = $STATE{'url'};
  $STATE{'cur_dir_name'} =~ s:^.*/([^/]+)/:$1:; #get last dir name from the url and remove all slashes
} else {
  # Still getting 500 error in browser?
  print "HTTP/1.1 404 Not Found\n";
  print "Content-type: text/html\n\n";
  #die; #die "404 Not Found\nYour requested folder $STATE{'url'} is not found\n";
}
$STATE{'title'} = getCurrentPageTitle($STATE{'url'}); # Figure out the title of the page

# FIGURE OUT IF ALL SETTINGS ARE THE DEFAULT
while ((my $key, my $value) = each(%DEFAULTS)) {
  if (${value} ne  $STATE{$key}) {
    $STATE{'is_default'} = 0;
    last;
  }
}

#DISPLAY MODE SETUP & DEFAULT
if ($STATE{'display_mode'} eq 'THUMBS') {
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_large'}; #max height of large thumbnail, normakky all will have same height
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_large'}; #max width of large thumbnail, normally never get this wide
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_large'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
} elsif ($STATE{'display_mode'} =~ /^SINGLE|SLIDESHOW$/) {
  #do not prefix image name, use full-size image
  $STATE{'prefix_cur'} = '';
  $STATE{'thumb_ext_cur'} = '';
} else {
  $STATE{'display_mode'} = "LIST";
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_small'}; #max dimension of small thumbnail
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_small'}; #max dimension of small thumbnail
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_small'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
}

# CONVIENIENCE VARIABLES
my ${icon_unknown} = "${assets_root}/icon_unknown$STATE{'prefix_cur'}gif";
my ${icon_folder} = "${assets_root}/icon_folder$STATE{'prefix_cur'}png";
my ${icon_music} = "${assets_root}/icon_music$STATE{'prefix_cur'}gif";
my ${icon_doc} = "${assets_root}/icon_doc$STATE{'prefix_cur'}gif";
my ${icon_copyleft} = "${assets_root}/icon_copyleft.png";
my ${database_file} = $STATE{'dir'}.'.jcdsee'; #SHOULD BE PUT INTO STATE

# BEGIN FUNCTIONS ============================================================================

sub buildDirList {
  my @database_raw = 'null';
  my @dir_list_raw = 'null';
  # TODO: Add param that allows to "refresh" the database with items newly added to the folder
  if (! -e ${database_file}) {
    opendir(DIR, $STATE{'dir'}) or die "Cant open this directory: \"$STATE{'dir'}\".";
    @dir_list_raw = readdir DIR;
    closedir(DIR);
    open(DATA,">>${database_file}") or die "Cant open file: \"${database_file}\".";
    # Filter the list to remove thumbnail images, hidden files and the stub script.
    foreach my ${line} (sort @dir_list_raw) {
      #Filter out the muck
      if ( ${line} !~ /^[.]|${script_name}/ ) {
        print DATA "${line}|\n";
      }
    }
    close(DATA);
  }
  open(DATA, ${database_file}) or die "Content-type: html/text\n\nCant open file: \"${database_file}\".";
  @database_raw = <DATA>;
  close(DATA);
  #PROCESS THE LIST
  my ${i} = 0;
  my ${j} = 0;
  # Fill file info arrays from data
  foreach my ${line} (@database_raw){
    chop(${line});
    my($file_name, $description) = split(/[|]/, $line);
    if (${file_name} ne '') {
      if ( ${file_name} =~ /[.](jp[e]?g|gif|png)$/i) { #File is an image
        $image_array[${i}] = ${file_name};
        $image_hash{${file_name}} = ${i};
        $file_types{${file_name}} = 'pic';
        ${i}++;
      } elsif ( -d "$STATE{'dir'}${file_name}") {
        #Folder
        $file_types{${file_name}} = 'folder';
      } elsif (${file_name} =~ /[.]mp3$|[.]wav$|[.]as[xf]$|[.]wm[a]$|[.]m3u$|[.]m[io]d$|[.]aif+$/i) {
        #Music (.mpeg,mpg,mp4,mp3,mp2,mp1,wav,asx,asf,wmx,wma,m3u,mid,mod,aif,aiff,qt)
        $file_types{${file_name}} = 'music';
      #} elsif (${file_name} =~ /[.](mp[e]?g|avi|mov|flv|wmv|qt)$/i) {
      # Video (.mpeg,mpg,avi,mov,flv,wmv,qt)
      # $file_types{${file_name}} = 'video';
      } elsif (${file_name} =~ /[.](pdf|doc|htm[l]?|txt|nfo|css|js)$/i) {
        #Text Document (pdf,doc,txt,htm,html,nfo,css,js)
        $file_types{${file_name}} = 'doc';
      } else {
        #Unknown file
        $file_types{${file_name}} = 'unknown';
      }
      $dir_list[${j}] = ${file_name};
      $file_descriptions{${file_name}} = ${description};
      ${j}++;
    }
  }
}

#   createImageThumbnail creates thumbs
#   createImageThumbnail("source", "destination thumb")
sub createImageThumbnail {
  my ${image_source} = $_[0];
  my ${image_thumb} = $_[1];
  my ${image_obj} = Image::Magick->new;
  ${tmp} = ${image_obj}->Read(${image_source}); warn ${tmp} if ${tmp};
  ${tmp} = ${image_obj}->Flatten(); # for PSD files
  # Resize to make large thumbnailes same height except in extremly wide images.  Small thumbs resize proportionally
  ${tmp} = ${image_obj}->Thumbnail(geometry=>"$IMAGE{'max_width'}x$IMAGE{'max_height'}", filter=>'Lanczos');
  # Cannot remove profile if $COMMANDLINE
  #${tmp} = ${image_obj}->Profile(name=>undef); warn ${tmp} if ${tmp};
  # Set JPEG compression level for thumb
  ${tmp} = ${image_obj}->Set(compression=>"JPEG");
  ${tmp} = ${image_obj}->Set(quality=>$IMAGE_GLOBAL{'thumb_quality'});
  ${tmp} = ${image_obj}->Set(type=>"Optimize");
  ${tmp} = ${image_obj}->Write(${image_thumb}); warn ${tmp} if ${tmp};
  @${image_obj} = (); # Clear memory
}

#   getImageTag returns an <img> tag. Will create thumbs if necessary.
#   getImageTag("file name without path","prefix for image")
sub getImageTag {
  my (${image_obj},${border},${alt},${tag});
  my ${image_name} = $_[0];
  my ${image_prefix} = $_[1];
  my ${image_thumb_name} = ${image_prefix}.${image_name}.$STATE{'thumb_ext_cur'};
  my ${image_thumb} = $STATE{'dir'}.${image_thumb_name}; #This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
  my ${image_thumb_url} = $STATE{'url'}.${image_thumb_name}; #Image url for browser
  # Make a Thumbnail if necessary
  # Datestamp isn't really important so i'm removing test to speed up display in 99% of cases
  # if ( ! (-e ${image_thumb}) || (((stat(${image_source}))[9]) > ((stat(${image_thumb}))[9])) ) {
  if ($STATE{'prefix_cur'} && ! (-e ${image_thumb})) {
    #Make a thumbnail of the image
    my ${image_source} = $STATE{'dir'}.${image_name};
    createImageThumbnail(${image_source}, ${image_thumb});
  }
  $image_thumb_url = escapeURL($image_thumb_url);
  $border = ($STATE{'display_mode'} eq 'LIST') ? '1' : '3';
  $alt = ($STATE{'display_mode'} eq 'THUMBS') ? stripHTML($file_descriptions{${image_name}}):'';
  ${tag} = "<img src='${image_thumb_url}' border='${border}' alt='${alt}'";
  if ($STATE{'display_mode'} eq 'SLIDESHOW') {
    ${tag} .= " id='big_pic' onabort='loaded()' onload='loaded()' onerror='loaded()'";
  }
  ${tag} .= " />";
  return ${tag};
}

#   getCurrentPageTitle() returns a SEO title for the current page which is reverse of path.
#   getCurrentPageTitle("url")
sub getCurrentPageTitle {
  my $path = $_[0];
  $path =~ s#${pic_root}|/$##g; # Delete pic root and trailing slash
  $path =~ s#/# : #g;# Replace all slashes with colon
  if ($STATE{'display_mode'} eq 'SINGLE') {
    $path .= ${title_char}.getNiceFilename($STATE{'pic_cur_file'});
  }
  $path = join($title_char, reverse(split($title_char, $path)));  # Split the path elements, then reassemble in reverse
  $path .= $STATE{'title'};
  $path = getNiceFilename($path);
  return $path;
}

#   getNiceFilename returns a string representing a filename with date prefix removed + dash, underscore replaced with space.
#   getNiceFilename("filename")
sub getNiceFilename {
  my $fn = $_[0];
  $fn = removeDatePrefix($fn);
  $fn = removeNumberPrefix($fn);
  $fn = removeFileExtension($fn);
  $fn =~ s#[._-]# #g;
  $fn =~ s#([[:lower:]])([[:upper:]\d])#\1 \2#g; # space out wiki words
  return $fn;
}

#   removeDatePrefix returns a string representing a filename with date prefix removed
#   removeDatePrefix("filename")
sub removeDatePrefix {
  my $fn = $_[0];
  $fn =~ s#(^| )\d\d\d\d-\d\d-\d\d_#\1#g; # Delete date prefixes
  return $fn;
}

#   removeNumberPrefix returns a string representing a filename with numbered prefix removed
#   removeNumberPrefix("filename")
sub removeNumberPrefix {
  my $fn = $_[0];
  $fn =~ s:^\d+_(.+):\1:g; # Delete number prefixes when there is a filename
  return $fn;
}

#   removeFileExtension returns a string representing a filename with the file extension removed
#   removeFileExtension("filename")
sub removeFileExtension {
  my $fn = $_[0];
  $fn =~ s#[.][A-Za-z]{3}$##g; # Delete 3-letter file extensions
  return $fn;
}

#   getSitemapData returns a piece of data from the sitemap XML database based on the "item" (pageDescription|pageDate|pageSize).
#   getSitemapData("dat
sub getSitemapData {
  my $item=$_[0];
  my $results = $stylesheet->transform($sitemap, NAME => "'$item'", VALUE => "'$STATE{'url_encoded'}'");
  my $string = $stylesheet->output_string($results);
  chomp($string);
  return $string;
}

#   gettitle returns an html formatted string representing the filename passed in
#   getTitle("file name to be parsed")
sub getTitle {
  #remove numbered prefix, extension and convert  _  into spaces.
  my ${file_name} = $_[0];
  my ${strip_date} = ($STATE{'display_mode'}  =~ /^THUMBS|SINGLE|SLIDESHOW$/)?1:0;
  if (${strip_date}) {
    return getNiceFilename(${file_name});
  } elsif (${file_name} =~ /^([0-9]{4}[-][0-9]{2}[-][0-9]{2})[_-]?(.*)/) { #DATED
    return "<span class='date'>${1}</span><span class='filename'>${2}</span>";
  } elsif (${file_name} =~ /^[0-9]+[_-](.+)/) { #NUMBERED
    return "<span class='date'>${1}</span>";
  } else {
    return "<span class='filename'>${file_name}</span>";
  }
}

#   stripHTML returns a string with HTMl tags removed and quotes encoded (used by alt tags)
#   stripHTML("string")
sub stripHTML {
  my ${string} = $_[0];
  ${string} =~ s/<[^>]+>//g;
  ${string} =~ s/"/&quot;/g; #quotes
  ${string} =~ s/'/&#39;/g; #apos
  return ${string};
}

#   escapeURL returns a URL with spaces escaped.
#   escapeURL("URL")
sub escapeURL {
  my $URL = $_[0];
  $URL =~ s: :%20:g;
  return $URL;
}

#   getHREF Builds a custom HREF given the object you want to link to.
#   getHREF(action[pic|dir|display_mode],  value[pic=url|dir=folder_name|display_mode])
sub getHREF {
 
  # display_mode
  #   dir          = norm
  #   pic          = do not use
  #   display_mode = use supplied
  # ---------------------------------------
  # *norm = use if not default.

  my ${action} = $_[0];
  my ${value} = $_[1];
  my ${HREF};
  #my $local_path = (${action} eq 'dir') ? ${value} : $STATE{'url'} ;
  #BASE SCRIPT NAME
  if (${action} eq 'dir') { 
    # Special case for dir when we can dump display_mode setting
    ${HREF} = "${value}";
    return ${HREF};
  } elsif (${action} eq 'dispaly_mode' && ${value} eq $DEFAULTS{'display_mode'}) { 
    # Special case when button turns it into the default
    ${HREF} = "$STATE{'url'}";
    return ${HREF};
  } else {
    ${HREF} = "${script_url}?";
  }
  #SET URL PARAM
  if (${action} eq 'pic') {
    ${HREF} .= "pic=$STATE{'url'}${value}";
  } elsif (${action} eq 'display_mode') {
    ${HREF} .= "pic=$STATE{'url'}$STATE{'pic_cur_file'}";
  } elsif (${action} eq 'dir') {
    ${HREF} .= "cur_url=${value}";
  }
  #DISPLAY MODE PARAM
  if (${action} ne 'pic' && ${action} ne 'dir') { #for 'pic' and 'dir' we have pre-defined display modes so they are excluded here
    if (${action} eq 'display_mode') {
      ${HREF} .= "${amp}display_mode=${value}";
    } else {
      ${HREF} .= "${amp}display_mode=$STATE{'display_mode'}"; #persist the display mode
    }
  }

  return escapeURL($HREF);
}

# Functions for file type booleans
# isFileType ("file name", "type")
sub isFileType {
  return ($file_types{$_[0]} eq $_[1])? 1:0; 
}

#   getDepthPath ()
sub getDepthPath {
  print '<a href="/">home</a>';
  foreach my ${path} (split( '/',$STATE{'url'})) {
    if (${path} ne '/') {
      $STATE{'url'} =~ m:(^/${path}/|^/.+/${path}/):;
      if (${1} ne '') {
        my $itemTitle = getNiceFilename(${path});
        print "/<a href=\"".getHREF('dir',${1})."\" title=\"${itemTitle}\">${itemTitle}</a>";
      }
    } else {
      print '@';
    }
  }
}

#   getIcon returns a linked image tag representing the file provided by $file_name
#   getIcon("name of file")
sub getIcon {
  my ${file_name} = $_[0];
  my ${link_content};
  my ${icon_file};
  my ${class};
  my ${desc} = ${file_name};
  ${desc} .= ($file_descriptions{${file_name}} ne "")? " - ".stripHTML($file_descriptions{${file_name}}) : "";
  if (isFileType(${file_name},'pic')) {
    #Image icon
    ${class} = ($STATE{'pic_cur_file'} eq ${file_name})? "current_pic" : "pic" ;
    ${link_content} = getImageTag(${file_name},$STATE{'prefix_cur'});
  } else {
    #we can create and upload a static thumbnail icon for any filetype... will replace default question mark
    my ${static_thumbnail_path} = $STATE{'dir'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
    #Use built-in icon
         if (isFileType(${file_name},'folder')) { ${icon_file} = ${icon_folder};
    } elsif (isFileType(${file_name},'doc')) {    ${icon_file} = ${icon_doc};
    } elsif (isFileType(${file_name},'music')) {  ${icon_file} = ${icon_music};
    } elsif (-e ${static_thumbnail_path}) {       ${icon_file} = $STATE{'url'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
    } else {                                      ${icon_file} = ${icon_unknown};
    }
    ${link_content} = "<img src=\"${icon_file}\" border=\"0\" alt=\"${desc}\" />"; # valign=\"middle\"
  }
  return getLinkTag(${file_name},${link_content},${desc},${class});
}

#   getLinkTag returns an <a> tag containing appropriate href based on the type of file, state, etc.
#   getLinkTag("name of file","link content","file description","CSS class name")
sub getLinkTag {
  my ${file_name} =    $_[0];
  my ${link_content} = $_[1];
  my ${desc} =         $_[2];
  my ${class} =        $_[3];
  my ${link_tag};
  #This is a bit annoying, see if google picks up the site 
  if (! "${desc}") {
    ${desc} = ${file_name};
    ${desc} .= ($file_descriptions{${file_name}} ne "")? " - ".stripHTML($file_descriptions{${file_name}}) : "";
  }
  if (isFileType(${file_name},'folder')) {
    #Folder
    ${link_tag} = "<a href=\"".getHREF('dir',"$STATE{'url'}${file_name}")."\" class=\"${class}\" title=\"${desc}\">${link_content}</a>\n";
  } elsif (isFileType(${file_name},'pic')) {
    #Image
    ${link_tag} = "<a href='".getHREF('pic',${file_name})."' class='${class}' title='${desc}'>".${link_content}.'</a>';
  } else {
    # Music, text or other.  Just link to the file
    ${link_tag} = "<a href='$STATE{'url'}${file_name}' class='${class}' title='${desc}'>${link_content}</a>\n";
  }
  return ${link_tag};
}

#   getNavButton("mode","value","text description")
sub getNavButton {
  my ${mode}=${_[0]};
  my ${value}=${_[1]};
  my ${desc}=${_[2]};
  my ${toggle} = (${value} eq $STATE{'display_mode'}) ? 'on' : 'off';
  my ${icon_modifier} = lc(${value}); #Lowercase
  my ${HREF};
  my ${rel} = '';
  if ($STATE{'display_mode'} eq ${value}) {
    ${HREF} = 'javascript:void(0)';
  } else {
    ${HREF} = getHREF(${mode} , ${value});
  }
  print "<a href='${HREF}' class='${toggle}' rel='nofollow' title='${desc}'><img src='${assets_root}/icon_button_${icon_modifier}.gif' border='0' alt='${desc}' width='30' height='30' /></a>";
}

# Dump out the simple image list & create thumbnails as needed - main loop
sub commandLineMakeThumbs {
  foreach my ${image_name} (@image_array) {
    my ${image_source} = $STATE{'dir'}.${image_name};
    print "  + ${image_source} : ";
    # Create small and large thumbnails as needed
    foreach my ${size} ('small', 'large') {
      my ${image_thumb_name} = $IMAGE_GLOBAL{'prefix_'.$size}.${image_name}.$STATE{'thumb_ext_cur'};
      my ${image_thumb} = $STATE{'dir'}.${image_thumb_name}; #This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
      print " [${size} :";
      # Make a Thumbnail if necessary
      if (! -e ${image_thumb}) {
        # Manually inject the correct width and height
        $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_'.$size};
        $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_'.$size};
        # Make a thumbnail of the image
        createImageThumbnail(${image_source}, ${image_thumb});
        print " OK, CREATED]";
      } else {
        print " OK, EXISTS]";
      }
    }
    print "\n";
  }
}

# Dump out the html formatted dir list - main loop
sub dumpDirList {
  #my(@time_info,@month_list);
  #my(${year},${month},${minute},${day},${hour},${file_size},${is_dir});
  my ${file_name};
  my @file_info;
  my ${file_size};
  #LIST AND THUMBNAIL DISPLAY MODES
  if ($STATE{'display_mode'} =~ /^(LIST|THUMBS)$/) {
    foreach ${file_name} (@dir_list) {
      ${file_size} = '';
      @file_info = stat $STATE{'dir'}.${file_name};
      #ALL THIS ISDIR SHOULD GO IN THE CACHE FILE!  ALSO NEED TO BE ABLE TO DELETE / RECACHE WITHOUT LOOSING INFO
      # Not used anymoer... ${is_dir} = S_ISDIR(${file_info[2]});
      if ($STATE{'display_mode'} eq "LIST") {
        #@time_info = localtime ${file_info[9]};
        #EXTRACT FILE INFO FROM ARRAY AND PAD
        #${year} = ${time_info[5]} + 1900;
        #${month} = (qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec)) [(${time_info[4]})];
        #${minute} = (${time_info[1]} < 10) ? "0".${time_info[1]} : ${time_info[1]};
        #${day} = (${time_info[3]} < 10) ? "0".${time_info[3]} : ${time_info[3]};
        #${hour} = (${time_info[2]} < 10) ? "0".${time_info[2]} : ${time_info[2]};
        if ( ! isFileType(${file_name},'folder')) {
          if (${file_info[7]} > 10000000) { 
            ${file_size} = int(${file_info[7]} / 1048576) . "&nbsp;MB";
          } elsif (${file_info[7]} > 1000000) { 
            ${file_size} = sprintf("%.1f", (${file_info[7]} / 1048576)) . "&nbsp;MB";
          } elsif (${file_info[7]} > 2047){
            ${file_size} = int(${file_info[7]} / 1024) . "&nbsp;KB";
          } elsif (${file_info[7]} > 1023){
            ${file_size} = sprintf("%.1f", (${file_info[7]} / 1024)) . "&nbsp;KB";
          } elsif (${file_info[7]} > 0){
            ${file_size} = ${file_info[7]} . "&nbsp;B";
          } else {
            ${file_size} = "0&nbsp;B";
          }
        }
        print "
        <tr>
          <td align='center'>";
            #GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
            print getIcon(${file_name});
            print "</td>
          <td class='l' width='100%'>";
            #date isn't really used, but maybe in future?
            #my ${date} = "${day}-${month}-${year} ${hour}:${minute}";
            print getLinkTag(${file_name},getTitle(${file_name}),'','simple');
            if ($file_descriptions{${file_name}}) {
              print "&nbsp;-&nbsp;$file_descriptions{${file_name}}";
            }
          print "</td>
          <td class='r'>${file_size}&nbsp;&nbsp;</td>
        </tr>";
      } elsif ($STATE{'display_mode'} eq "THUMBS") {
        #GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
        print '<table border="0" class="thumbBlock" cellpadding="0" cellspacing="1"><tr><td valign="middle" align="center">';
        print getIcon(${file_name});
        print '</td></tr><tr><td valign="top" class="thumb_file_name" align="center">'.getTitle(${file_name}).'</td></tr></table>';
      }
    }
    if ($STATE{'display_mode'} eq 'THUMBS') {
      print '<div>&nbsp;</div>';
    }
  } elsif ($STATE{'display_mode'} eq 'SINGLE') {
    #SINGLE IMAGE MODE
    #Make sure large thumbs exist
    ${file_name} = $STATE{'pic_cur_file'};
    if (${file_name}) {
      ${tmp} = getImageTag($STATE{'pic_previous_file'},$IMAGE_GLOBAL{'prefix_large'});
      ${tmp} = getImageTag($STATE{'pic_next_file'},$IMAGE_GLOBAL{'prefix_large'});
      print "
      <table class='singleImage' border='0' cellspacing='8' cellpadding='0'>
        <tr>
          <td align='center' colspan='3'><div class='header' id='description'><strong>".getTitle(${file_name})." ($STATE{'pic_cur_number'} of $STATE{'pic_array_length'} images)</strong>";
            if ($file_descriptions{${file_name}}) {
              print " - $file_descriptions{${file_name}}";
            }
            print "</div></td>
        </tr>
        <tr>
          <td align='center' class='trans'><a title='Previous image' href='".getHREF('pic',$STATE{'pic_previous_file'})."' class='pic'><img src='$STATE{'url'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_previous_file'}$IMAGE_GLOBAL{'thumb_ext'}' alt='' id='PREVIOUS'></a></td>
          <td><span class='big_pic'><a href='".getHREF('display_mode','SLIDESHOW')."' title='Slideshow...' class='current_pic'>".getImageTag(${file_name},'')."</a></span></td>
          <td align='center' class='trans'><a title='Next image' href='".getHREF('pic',$STATE{'pic_next_file'})."' class='pic'><img src='$STATE{'url'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_next_file'}$IMAGE_GLOBAL{'thumb_ext'}' alt='' id='NEXT'></a></td>
        </tr>
      </table>
      <br />
      ";
    } else {
      #COPIED TWICE. Move this to the top... mode should change to list if there are no images...
      print '<script language="Javascript" type="text/javascript"> refresh("display_mode","LIST"); </script>';
    }
  } elsif ($STATE{'display_mode'} eq 'SLIDESHOW') {
    #SLIDESHOW IMAGE MODE
    #Make sure large thumbs exist
    ${file_name} = $STATE{'pic_cur_file'};
    if (${file_name}) {
      print "
      <table border='0' cellspacing='4' cellpadding='0' width='100%'>
        <tr>
          <td width='50%' rowspan='2'>&nbsp;</td>
          <td align='center'><div class='header' id='desc'><strong>".getTitle(${file_name})." ($STATE{'pic_cur_number'} of $STATE{'pic_array_length'} images)</strong>";
            if ($file_descriptions{${file_name}}) {
              print " - $file_descriptions{${file_name}}";
            }
            print "</div></td>
          <td width='50%' rowspan='2'>&nbsp;</td>
        </tr>
        <tr>
          <td><span class='big_pic'>".getImageTag(${file_name},'')."</span></td>
        </tr>
      </table>
      <br />
      ";
    } else {
      #COPIED TWICE. Move this to the top... mode should change to list if there are no images... may be cause of bug???
      print '<script language="Javascript" type="text/javascript"> refresh("display_mode","LIST"); </script>';
    }
  }  
}

# This function figures out the page context, setting, etc. based on the current url.
sub calculateImageListState {
  if (@image_array > 0) {
    $STATE{'pic_last_idx'}         = $#{image_array};
    $STATE{'pic_array_length'}     = $STATE{'pic_last_idx'} + 1;
    if ($STATE{'pic_cur_file'}){
      if ( "$image_hash{ $STATE{'pic_cur_file'} }" ne "" ){
        $STATE{'pic_cur_idx'} = $image_hash{ $STATE{'pic_cur_file'} };
      } else {
        $ERROR=1;
        $DUMP.="DID NOT FIND '$STATE{'pic_cur_file'}' IN THE LIST!<br>";
      }
    }
    $STATE{'pic_next_idx'}         = $STATE{'pic_cur_idx'} + 1;
    $STATE{'pic_previous_idx'}     = $STATE{'pic_cur_idx'} - 1;
    # This chunk will just loop the image array around if it is out of bounds.
    if ($STATE{'pic_cur_idx'}     >= $STATE{'pic_last_idx'}){
      $STATE{'pic_cur_idx'}        = $STATE{'pic_last_idx'};
      $STATE{'pic_next_idx'}       = 0;
      $STATE{'pic_previous_idx'}   = $STATE{'pic_cur_idx'} - 1;
    } elsif ($STATE{'pic_cur_idx'} <= 0) {
      $STATE{'pic_cur_idx'}        = 0;
      $STATE{'pic_next_idx'}       = $STATE{'pic_cur_idx'} + 1;
      $STATE{'pic_previous_idx'}   = $STATE{'pic_last_idx'};
    }
    $STATE{'pic_cur_number'}       = $STATE{'pic_cur_idx'}  + 1;
    $STATE{'pic_cur_file'}         = ${image_array[ $STATE{'pic_cur_idx'} ]};
    $STATE{'pic_previous_file'}    = ${image_array[ $STATE{'pic_previous_idx'} ]};
    $STATE{'pic_next_file'}        = ${image_array[ $STATE{'pic_next_idx'} ]};
   }
  #Would be ideal if we did'nt unencode then re-encode the url_encoded.  In many cases, $ENV{REQUEST_URI} has what we need!
  #Problem is that there are several ways to get the 'url' (cur_url or directly from path if no mod_re-write)
  $STATE{'url_encoded'} = $STATE{'url'};
  $STATE{'url_encoded'} =~ s/ /%20/g;
  $STATE{'page_description'} = stripHTML(getSitemapData('pageDescription'));
}

# GET READY TO PARTY!
buildDirList();
calculateImageListState();

if (${COMMANDLINE}) {
  # print "display_mode : $STATE{'display_mode'}\n";
  commandLineMakeThumbs();
  print "[done]\n";
  exit 0;
}

# RENDER HTML ==================================================================================================
# RENDER HEAD
print "Content-type: text/html\n\n";
print "<!DOCTYPE html>
<html>
  <head>
    <meta charset='utf-8' />
    <title>$STATE{'title'}</title>
    <meta http-equiv='imagetoolbar' content='no' />
    <meta name='description' content='$STATE{'page_description'}' />
    <meta name='keywords' content='travel photography,Jonathan Cross, pics, photos, India, Sri lanka, laos, cambodia, vietnam, indonesia, bangladesh' />
    <link href='${assets_root}/jcdsee.css' rel='stylesheet' type='text/css' />
    <!--[if lt IE 8]>  <script src='${assets_root}/IE8/IE8.js' type='text/javascript'></script>  <![endif]-->
    <script src='${assets_root}/jcdsee.js' type='text/javascript'></script>";
############
# Get the description here
#
if ($STATE{'display_mode'}  =~ /^SINGLE|SLIDESHOW$/) {
   #Allows IE to fade between pages
   print '<meta http-equiv="Page-Exit" content="progid:DXImageTransform.Microsoft.Fade(duration=0.8,overlap=0.8)" />';
}
if ($STATE{'display_mode'} eq "SLIDESHOW") {
print "
<script language='javascript' type='text/javascript'>
  var url=\"$STATE{'url'}\"
  var cur_pic=$STATE{'pic_cur_idx'};
  var image_array=new Array(";
  # This should be moved to DOM
  my $len=$#{image_array};
  for (my $i=0;$i<=$len;$i++) {
    print "\n'".$image_array[$i]."'";
    if ($i!=$len) { print "," };
  }

  print "
  );
  var descriptions_array=new Array(";
  for (my $i=0;$i<=$len;$i++) {
  my $desc=$file_descriptions{$image_array[$i]};
  $desc=~s/'/&#39;/g;
  print "\n'".$desc."'";
  if ($i!=$len) { print "," };
} 
print "
);
</script>
";
}

my ${onload}='';
if ($STATE{'display_mode'} eq 'SLIDESHOW') {
  ${onload}="startSlideshow();";
} elsif ($STATE{'display_mode'} eq 'SINGLE') {
  ${onload}="cacheImages('$STATE{'url'}$STATE{'pic_previous_file'}','$STATE{'url'}$STATE{'pic_next_file'}');";
}

if ($STATE{'test_mode'}) {
  # make it pink if in test mode
  print "<style type='text/css'> body {border:10px solid red;margin:0;padding:5px;} </style>";
}

if ($STATE{'display_mode'} eq 'SINGLE' && $STATE{'pic_array_length'} <= 1) {
  # This is sloppy, I should not send the code if its not needed
  print "<style type='text/css'> .trans {display:none;} </style>";
}

print "
  </head>
  <body class=\"$STATE{'display_mode'}\" onload=\"${onload}\"><div id=\"page\">";
#    <noscript>
#      ";
#  foreach my ${file_name} (@image_array) {
#    print '<a href="'.$STATE{'url'}.${file_name}.'">'.${file_name};
#    if ($file_descriptions{${file_name}}) {
#      print ' - '.stripHTML($file_descriptions{${file_name}});
#    }
#    print "</a>";
#  }
#  </noscript>
print "
    <div id='admin_button' role='link' onclick=\"window.open('${assets_root}/admin/index.cgi?display_url${amp}cur_url=$STATE{'url'}')\" title='Login'></div>
    <!-- Begin Controls -->
    <table id='control_table' cellpadding='4' cellspacing='0' border='0'>
      <tr>
        <td id='depthPath' width='100%'>";
          #GENERATE THE DEPTH PATH
          getDepthPath();
          print '</td>
        <td id="buttons" nowrap="nowrap">';
          getNavButton("display_mode","LIST","LIST MODE");
          getNavButton("display_mode","THUMBS","THUMBNAIL IMAGE MODE");
          getNavButton("display_mode","SINGLE","SINGLE IMAGE MODE");
          getNavButton("display_mode","SLIDESHOW","SLIDESHOW DISPLAY MODE");
          print '</td>
        </tr>';
      if ($STATE{'display_mode'} eq "SLIDESHOW") {
        print '
          <tr>
          <td colspan="2">
            <table cellpadding="0" cellspacing="0" border="0" id="slideshowControls">
              <tr>
                <td>SLIDESHOW:&nbsp;&nbsp;</td>
                <td nowrap="nowrap">
                  <a href="javascript:startSlideshow()" id="startLink" class="slideButtonStart">play</a>&nbsp;
                  <a href="javascript:stopSlideshow()" id="stopLink" class="slideButton">pause</a>&nbsp;
                  <a href="javascript:document.location.replace(document.location.href)" class="slideButton">reset</a>
                </td>
                <td width="100%" style="text-align:center;">
                  <span id="count">'.$STATE{'pic_cur_number'}.' of '.$STATE{'pic_array_length'}.'</span>
                </td>
                <td align="right" style="text-align:right;">speed:&nbsp;</td>
                <td>
                  <div id="select_container">
                    <select name="speedMenu" onchange="changeSpeed(this.selectedIndex);"><option selected="selected" value="normal">Normal</option><option value="slow">Slow</option><option value="fast">Fast</option></select>
                  </div>
                </td>
              </tr>
            </table>
          </td>
          </tr>
        ';
      }
      print '
      </table>
      <form name="control_form" id="control_form" method="post" action="'.$STATE{'url'}.'" target="_self">
        <input type="hidden" name="display_mode" value="'.$STATE{'display_mode'}.'">
        <input type="hidden" name="pic_cur_idx" value="'.$STATE{'pic_cur_idx'}.'">
      </form>';
      if ($STATE{'display_mode'} eq "LIST") {
        print '<div id="pageDescription"><strong>'.$STATE{'cur_dir_name'}.'</strong>';
        if ("$STATE{'page_description'}") {
          print ${title_char}.$STATE{'page_description'};
        }
        print '</div>';
        print '
        <table id="file_list" cellpadding="4" cellspacing="0" border="0">';
      }
      #CALL THE LOOP THAT RENDERS THE FILE LIST
      dumpDirList();
      #FINISH TABLE FOR LIST
      if ($STATE{'display_mode'} eq "LIST") {
        print '
        </table>
        ';
      }

# CREATIVE COMMONS LICENSE
print '
<!-- 
<rdf:RDF xmlns="http://web.resource.org/cc/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <Work rdf:about="">
    <license rdf:resource="http://creativecommons.org/licenses/by-nc-sa/2.5/" />
    <dc:title>Photography by Jonathan Cross</dc:title>
    <dc:description>Various photos from around the world.</dc:description>
    <dc:creator><Agent><dc:title>Jonathan Cross</dc:title></Agent></dc:creator>
    <dc:rights><Agent><dc:title>Jonathan Cross</dc:title></Agent></dc:rights>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
    <dc:source rdf:resource="http://pics.jonathancross.com" />
  </Work>
  <License rdf:about="http://creativecommons.org/licenses/by-nc-sa/2.5/">
    <permits rdf:resource="http://web.resource.org/cc/Reproduction"/>
    <permits rdf:resource="http://web.resource.org/cc/Distribution"/>
    <requires rdf:resource="http://web.resource.org/cc/Notice"/>
    <requires rdf:resource="http://web.resource.org/cc/Attribution"/>
    <prohibits rdf:resource="http://web.resource.org/cc/CommercialUse"/>
    <permits rdf:resource="http://web.resource.org/cc/DerivativeWorks"/>
    <requires rdf:resource="http://web.resource.org/cc/ShareAlike"/>
  </License>
</rdf:RDF>
-->
';
#DEBUG ERROR INFORMATION
if (${ERROR}) {
  ${DUMP} .=  "FILE TYPES: \n";
  foreach my $k (sort keys %file_types) {
    ${DUMP} .= "  $k = $file_types{$k}\n";
  }
  ${DUMP} .=  "\nIMAGES: \n";
  foreach my $k (sort keys %image_hash) {
    ${DUMP} .= "  $k = $image_hash{$k}\n";
  }
  ${DUMP} .=  "\nSTATE: \n";
  foreach my $k (sort keys %STATE) {
    ${DUMP} .= "  $k = $STATE{$k}\n";
  }
  print "
    <div style='margin-top:11px;width:560px;border:2px solid red;background-color:#f99;font-size:9px;font-family:verdana,sans-serif;color:#a00;'>
      <b style='font-size:10px;color:black;'>ERROR:</b><br />
      <pre>${DUMP}</pre>
    </div>";
}

#HIDE STATS FOR SLIDESHOW MODE
if ($STATE{'display_mode'} ne "SLIDESHOW") {
$TIMER{'total_e'} = gettimeofday();
$TIMER{'total'} = sprintf("%.3f", ($TIMER{'total_e'} - $TIMER{'total_s'}));
print '
<br style="line-height:15px;">
<table border="0" cellpadding="0" cellspacing="0"><tr>
  <td valign="top">
    <div id="copyleft">
      <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/3.0/" target="_blank"><img alt="Creative Commons License" border="0" src="'.${icon_copyleft}.'" /></a>
    </div>
  </td>
  <td>
    <div id="usage">';
      print "
      <a href='/jcdsee_latest.txt' title='View the latest source code behind this website.'>JCDSee ${VERSION}</a><br>
      Script executed in: $TIMER{'total'} seconds.";
      if (${country_code}) {
        print " Geo: $ENV{'HTTP_CF_IPCOUNTRY'}";
      }
      print '<br>';
      print getSitemapData('pageDate');
      print getSitemapData('pageSize');
      print "
    </div>
  </td></tr></table>";
}
print "
    <div style='height:300px;visibility:hidden;'>&nbsp;</div>
    </div>
  </body>
</html>
";
