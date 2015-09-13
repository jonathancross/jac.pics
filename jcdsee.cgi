#!/usr/bin/perl
#
my $VERSION = '2.0.1';
#
# JCDSee by Jonathan Cross : www.JonathanCross.com
# See GitHub for license, usage, examples and more info:
#  • https://github.com/jonathancross/pics.jonathancross.com
#
# WISHLIST / FIXES / TODOs:
#  - Simplify this script and move view settings into browser.
#  - Load and cache all file info just once.
#  - Inline player for video & audio. html5 video?
#  - Nonlinear slideshow with thumbs, next and previous.
#    Then merge "single" mode with "slideshow".
#  - PSD icons: complex to flatten...
#  - Convert databases to JSON.
#  - Allow in-browser editing of descriptions.
#  - Non-destructive folder "refresh" when files are added or removed.
#
################################################################################

use strict;
use Image::Magick;
use CGI ':standard';
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':mode';
use Time::HiRes 'gettimeofday';
use XML::LibXSLT;
use XML::LibXML;

my %TIMER;
$TIMER{'total_s'} = gettimeofday();

# Allow command line execution / debugging
my ${COMMANDLINE} = 0;
if ( defined($ARGV[0]) && ($ARGV[0] eq 'debug') ) {
  ${COMMANDLINE} = 1;
  print "\nDEBUG MODE - Version: $VERSION\n\n";
}

# GLOBAL VARIABLES #############################################################
# DIRECTORY LIST ARRAYS
my(@dir_list, @image_array, %image_hash, %file_descriptions, %file_types);
my ${tmp};
my ${DUMP} = '';
my ${ERROR} = 0;
my ${root} = (${COMMANDLINE}) ? '.' : $ENV{DOCUMENT_ROOT};
my ${pic_root} = '/pics';
my ${assets_root} = '/jcdsee'; # Folder containing assets used by this script. (icons, buttons, css, etc)
my ${script_name} = 'jcdsee.cgi'; # Name of the stub script, we need this so we don't show it in the dir listing.
my ${database_file_name} = '.jcdsee'; # Filename used for each folder's database.
my ${script_url} = "/${script_name}"; # The main script URL used in links.
my ${test_url} = 'test'; # Special test mode staging url
my ${title_char} = ' : ';
my $amp = '&amp;';
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

# CONSTANTS FOR IMAGE PROCESSING
my %IMAGE_GLOBAL = (
  thumb_quality     => 80,     # Thumbnail jpeg quality
  max_width_small   => 50,     # Max width of small thumbs
  max_width_large   => 400,    # Max width of large thumbs
  max_height_small  => 50,     # Max height of small thumbs
  max_height_large  => 140,    # Max height of large thumbs
  prefix_small      => '.S.',  # File name prefix to use for Small generated thumbnail images
  prefix_large      => '.L.',  # File name prefix to use for Large generated thumbnail images
  thumb_ext         => '.jpg'  # File extension of generated thumbnail images
);

# VARS FOR CURRENT IMAGE PROCESSING STATE, PERHAPS SHOULD BE MOVED TO %STATE ?
my %IMAGE = (
  max_width         => 0,      #Max width placeholder
  max_height        => 0       #Max height placeholder
);

# DISPLAY STATE VARS
my %STATE = (
  country_code      => (${COMMANDLINE}) ? 'none' : $ENV{'HTTP_CF_IPCOUNTRY'},
  database_file     => '', # Full server path to the .jcdsee database file.
  server_dir        => '', # Full server path to the folder being listed.
  web_dir           => '', # The path from the webserver document root.
  web_dir_encoded   => '', # The path from the webserver document root. (URL encoded)
  is_deprecated_param => 0,  # Identifies requests using 'cur_url' or 'pic' params which are deprecated.
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
  pic_cur_file      => '', # Filename of the currently selected image.
  pic_next_file     => '',
);
my %DEFAULTS = (
  display_mode      => 'LIST',
  test_mode         => 0,
);

# LOAD / SET PARAMS & DEFAULTS
$STATE{'display_mode'} = param('display_mode');
$STATE{'test_mode'} = ( $ENV{SERVER_NAME} =~ /^$test_url/ ) ? 1 : 0;

# CURRENT URL FROM PARAM -OR- PATH

# Deprecated old params: 'cur_url' and 'pic'.
if (param('cur_url') || param('pic')) {
  $STATE{'is_deprecated_param'} = 1;
  if (param('cur_url')) {
    $STATE{'web_dir'} = param('cur_url');
    $STATE{'web_dir'} =~ s:[^/]$:$&\/:;
    $STATE{'display_mode'} ||= 'LIST';
  } elsif (param('pic') && (param('pic') =~ m:(.*/)(.*):) ) {
    # Get picture path from the pic param.
    $STATE{'web_dir'} = $1;
    $STATE{'pic_cur_file'} = $2;
    $STATE{'display_mode'} ||= 'SINGLE';
  }
}

# New 'pic_path' param to replace 'pic' and 'cur_url'.
# Will override others if specified.
if (param('pic_path') && (param('pic_path') =~ m:(.*/)(.*):) ) {
  $STATE{'is_deprecated_param'} = 0;
  $STATE{'web_dir'} = $1;
  # Leave display_mode as-is so we can define below based on # of images found, etc.
  if ($2) {
    $STATE{'pic_cur_file'} = $2;
  }
}

# Use current URI for the path.  This should probably be deprecated as it was
# used when we soft linked the CGI script into every folder. Now we just use
# apache mod rewrite to send as param.
if ($STATE{'web_dir'} eq '') {
  $STATE{'web_dir'} = $ENV{REQUEST_URI};
  $STATE{'web_dir'} =~ s/%20/ /g;
  $STATE{'display_mode'} ||= $DEFAULTS{'display_mode'};
}

if (${COMMANDLINE}) {
  $STATE{'web_dir'} = (${ARGV[1]}) ? ${ARGV[1]} : "${root}${pic_root}"; # HAVE DIR DEFAULT TO "." FOR COMMANDLINE DEBUGGING
  $STATE{'server_dir'} = $STATE{'web_dir'};
  $STATE{'display_mode'} = ${ARGV[2]};
  $STATE{'pic_cur_idx'} = int(${ARGV[3]});
} elsif ($STATE{'web_dir'} =~ m:^/: && $STATE{'web_dir'} !~ m:/[.][.]: && -d $ENV{DOCUMENT_ROOT}.$STATE{'web_dir'}){ # Have to validate the directory for security reasons
  $STATE{'server_dir'} = $ENV{DOCUMENT_ROOT}.$STATE{'web_dir'};
  $STATE{'cur_dir_name'} = $STATE{'web_dir'};
  $STATE{'cur_dir_name'} =~ s:^.*/([^/]+)/:$1:; # Get last dir name from the url and remove all slashes.
} else {
  # File not found error.
  print "HTTP/1.1 404 Not Found\n";
  print "Content-type: text/html\n\n";
  #die; #die "404 Not Found\nYour requested folder $STATE{'web_dir'} is not found\n";
}

$STATE{'database_file'} = $STATE{'server_dir'}.${database_file_name};

# Load  / Build the list of files.
loadFileDatabase();

# Default to first image if possible for SINGLE and SLIDESHOW. Fixes issue #17.
if ($STATE{'display_mode'} =~ /^SINGLE|SLIDESHOW$/ && ! $STATE{'pic_cur_file'} && @image_array) {
  $STATE{'pic_cur_file'} = $image_array[0];
}

$STATE{'title'} = getCurrentPageTitle($STATE{'web_dir'}); # Figure out the title of the page

# Figure out if all settings are same as the default.
while ((my $key, my $value) = each(%DEFAULTS)) {
  if (${value} ne  $STATE{$key}) {
    $STATE{'is_default'} = 0;
    last;
  }
}

# Display mode setup & defaults.
if ($STATE{'display_mode'} eq 'THUMBS') {
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_large'}; #max height of large thumbnail, normally all will have same height
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_large'}; #max width of large thumbnail, normally never get this wide
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_large'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
} elsif ($STATE{'display_mode'} =~ /^SINGLE|SLIDESHOW$/ && $STATE{'pic_cur_file'}) { # Only allow SINGLE|SLIDESHOW if there is 1 or more images.
  # Do not prefix image name, use full-size image
  $STATE{'prefix_cur'} = '';
  $STATE{'thumb_ext_cur'} = '';
} else {
  $STATE{'display_mode'} = 'LIST';
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_small'}; #max dimension of small thumbnail
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_small'}; #max dimension of small thumbnail
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_small'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
}

# CONVIENIENCE VARIABLES
my ${icon_unknown} = "${assets_root}/icon_unknown$STATE{'prefix_cur'}png";
my ${icon_folder} = "${assets_root}/icon_folder$STATE{'prefix_cur'}png";
my ${icon_music} = "${assets_root}/icon_music$STATE{'prefix_cur'}png";
my ${icon_doc} = "${assets_root}/icon_doc$STATE{'prefix_cur'}png";
my ${icon_copyleft} = "${assets_root}/icon_copyleft.png";


# Builds image_array, image_hash, file_descriptions, file_types, and dir_list.
#   loadFileDatabase()
sub loadFileDatabase {
  my (@database_raw, @dir_list_raw);
  # Create the database if it doesn't exist yet.
  if (! -e $STATE{'database_file'}) {
    createDatabase();
  }
  # Now that we have a database for sure, load in the data.
  open(DATA, $STATE{'database_file'}) or die "Content-type: html/text\n\nCant open file: \"$STATE{'database_file'}\".";
  @database_raw = <DATA>;
  close(DATA);
  # Process the database contents.
  my ${img_count} = 0;
  my ${file_count} = 0;
  # Fill file info arrays from data.
  foreach my ${line} (@database_raw){
    chop(${line});
    # TODO: Allow first line to contain meta data?
    my($file_name, $description) = split(/[|]/, $line);
    if (${file_name} ne '') {
      if (${file_name} =~ /[.](jp[e]?g|gif|png)$/i) {
        # Picture
        $image_array[${img_count}] = ${file_name};
        $image_hash{${file_name}} = ${img_count};
        $file_types{${file_name}} = 'pic';
        ${img_count}++;
      } elsif (-d "$STATE{'server_dir'}${file_name}") {
        # Folder
        $file_types{${file_name}} = 'folder';
      } elsif (${file_name} =~ /[.]mp3$|[.]wav$|[.]as[xf]$|[.]wm[a]$|[.]m3u$|[.]m[io]d$|[.]aif+$/i) {
        # Music (.mpeg,mpg,mp4,mp3,mp2,mp1,wav,asx,asf,wmx,wma,m3u,mid,mod,aif,aiff,qt)
        $file_types{${file_name}} = 'music';
      #} elsif (${file_name} =~ /[.](mp[e]?g|avi|mov|flv|wmv|qt)$/i) {
      # Video (.mpeg,mpg,avi,mov,flv,wmv,qt)
      # $file_types{${file_name}} = 'video';
      } elsif (${file_name} =~ /[.](pdf|doc|htm[l]?|txt|nfo|css|js)$/i) {
        # Text Document (pdf,doc,txt,htm,html,nfo,css,js)
        $file_types{${file_name}} = 'doc';
      } else {
        # Unknown file
        $file_types{${file_name}} = 'unknown';
      }
      $dir_list[${file_count}] = ${file_name};
      $file_descriptions{${file_name}} = ${description};
      ${file_count}++;
    }
  }
}

# Creates the .jcdsee database file if it doesn't exist yet.
# TODO: Allow database updates with items newly added to the folder.
#   createDatabase()
sub createDatabase {
  opendir(DIR, $STATE{'server_dir'}) or die "Cant open this directory: \"$STATE{'server_dir'}\".";
  my @dir_list_raw = readdir DIR;
  closedir(DIR);
  open(DATA, ">>$STATE{'database_file'}") or die "Cant open file: \"$STATE{'database_file'}\".";
  # Write filtered list out to the .jcdsee database file.
  foreach my ${line} (sort @dir_list_raw) {
    # Exclude thumbnail images, hidden files and the jcdsee script itself.
    if (${line} !~ /^[.]|${script_name}/) {
      print DATA "${line}|\n";
    }
  }
  close(DATA);
}

# Creates a thumbnail image.
#   createImageThumbnail("source", "destination thumb")
sub createImageThumbnail {
  my ($image_source, $image_thumb) = @_;
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

# Returns an <img> tag. Will create thumbs if necessary.
#   getImageTag("file name without path", "prefix for image")
sub getImageTag {
  my ($image_name, $image_prefix) = @_;
  my ${image_thumb_name} = ${image_prefix}.${image_name}.$STATE{'thumb_ext_cur'};
  my ${image_thumb} = $STATE{'server_dir'}.${image_thumb_name}; #This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
  my ${image_thumb_url} = $STATE{'web_dir'}.${image_thumb_name}; #Image url for browser
  # Make a Thumbnail if necessary
  # Datestamp isn't really important so i'm removing test to speed up display in 99% of cases
  # if ( ! (-e ${image_thumb}) || (((stat(${image_source}))[9]) > ((stat(${image_thumb}))[9])) ) {
  if ($STATE{'prefix_cur'} && ! (-e ${image_thumb})) {
    #Make a thumbnail of the image
    my ${image_source} = $STATE{'server_dir'}.${image_name};
    createImageThumbnail(${image_source}, ${image_thumb});
  }
  $image_thumb_url = escapeURL($image_thumb_url);
  my $alt = ($STATE{'display_mode'} eq 'THUMBS') ? stripHTML($file_descriptions{${image_name}}) : '';
  return "<img src='${image_thumb_url}' class='picture-icon' alt='${alt}'>";
}

# Returns a SEO title for the current page which is reverse of path.
#   getCurrentPageTitle("path")
sub getCurrentPageTitle {
  my ($path) = @_;
  $path =~ s@${pic_root}|/$@@g; # Delete pic root and trailing slash.
  $path =~ s@/@ : @g; # Replace all slashes with colon.
  if ($STATE{'display_mode'} eq 'SINGLE') {
    $path .= ${title_char}.getNiceFilename($STATE{'pic_cur_file'});
  }
  $path = join($title_char, reverse(split($title_char, $path)));  # Split the path elements, then reassemble in reverse
  $path .= $STATE{'title'};
  $path = getNiceFilename($path);
  return $path;
}

# Returns a string representing a filename with date prefix removed + dash, underscore replaced with space.
#   getNiceFilename("filename")
sub getNiceFilename {
  my ($fn) = @_;
  $fn = removeDatePrefix($fn);
  $fn = removeNumberPrefix($fn);
  $fn = removeFileExtension($fn);
  $fn =~ s#[._-]# #g;
  $fn =~ s#([[:lower:]])([[:upper:]\d])#\1 \2#g; # space out wiki words
  return $fn;
}

# Returns a string representing a filename with date prefix removed.
#   removeDatePrefix("filename")
sub removeDatePrefix {
  my ($fn) = @_;
  $fn =~ s@(^| )\d\d\d\d-\d\d-\d\d_@\1@g; # Delete date prefixes
  return $fn;
}

# Returns a string representing a filename with numbered prefix removed.
#   removeNumberPrefix("filename")
sub removeNumberPrefix {
  my ($fn) = @_;
  $fn =~ s:^\d+_(.+):\1:g; # Delete number prefixes when there is a filename
  return $fn;
}

# Returns a string representing a filename with the file extension removed.
#   removeFileExtension("filename")
sub removeFileExtension {
  my ($fn) = @_;
  $fn =~ s#[.][A-Za-z]{3}$##g; # Delete 3-letter file extensions
  return $fn;
}

# Returns a piece of data from the sitemap XML database based on the "item" (pageDescription|pageDate|pageSize).
#   getSitemapData("databaseItem")
sub getSitemapData {
  my ($item) = @_;
  my $results = $stylesheet->transform($sitemap, NAME => "'$item'", VALUE => "'$STATE{'web_dir_encoded'}'");
  my $string = $stylesheet->output_string($results);
  chomp($string);
  return $string;
}

# Returns an html formatted string representing the filename passed in.
#   getParsedFileName("file name to be parsed")
sub getParsedFileName {
  my ($file_name) = @_;
  my ${strip_date} = ($STATE{'display_mode'} =~ /^THUMBS|SINGLE|SLIDESHOW$/) ? 1 : 0;
  my ${file_name_parsed} = '<span class="file-name-container">';
  if (${strip_date}) {
    ${file_name_parsed} .= getNiceFilename(${file_name});
  } elsif (${file_name} =~ /^([0-9]{4}[-][0-9]{2}[-][0-9]{2})[_-]?(.*)/) { # DATED
    ${file_name_parsed} .= "<span class='file-date'>${1}</span> <span class='file-name file-name-dated'>${2}</span>";
  } elsif (${file_name} =~ /^[0-9]+[_-](.+)/) { # NUMBERED
    ${file_name_parsed} .= "<span class='file-name file-name-numbered'>${1}</span>";
  } else {
    ${file_name_parsed} .= "<span class='file-name'>${file_name}</span>";
  }
  return ${file_name_parsed} .= '</span>';
}

# Returns a string with HTMl tags removed and quotes encoded (used by alt tags)
#   stripHTML("string")
sub stripHTML {
  my ($string) = @_;
  ${string} =~ s/<[^>]+>//g;
  ${string} =~ s/"/&quot;/g; # quotes: "
  ${string} =~ s/'/&#39;/g; # apos: '
  return ${string};
}

# Returns a URL with spaces escaped.
#   escapeURL('url')
sub escapeURL {
  my ($url) = @_;
  $url =~ s: :%20:g;
  return $url;
}

# Builds a custom HREF given the object you want to link to.
#   getHREF(action[pic|dir|display_mode],  value[pic=url|dir=folder_name|display_mode])
sub getHREF {
  my ($action, $value) = @_;

  # display_mode
  #   dir          = norm
  #   pic          = do not use
  #   display_mode = use supplied
  # ---------------------------------------
  # *norm = use if not default.

  my ${HREF};
  # my $local_path = (${action} eq 'dir') ? ${value} : $STATE{'web_dir'} ;
  # BASE SCRIPT NAME
  if (${action} eq 'dir') {
    # Special case for dir when we can dump display_mode setting
    ${HREF} = "${value}";
    return ${HREF};
  } elsif (${action} eq 'dispaly_mode' && ${value} eq $DEFAULTS{'display_mode'}) {
    # Special case when button turns it into the default
    ${HREF} = "$STATE{'web_dir'}";
    return ${HREF};
  } else {
    ${HREF} = "${script_url}?";
  }
  # SET URL PARAM
  if (${action} eq 'pic') {
    ${HREF} .= "pic=$STATE{'web_dir'}${value}";
  } elsif (${action} eq 'display_mode') {
    ${HREF} .= "pic=$STATE{'web_dir'}$STATE{'pic_cur_file'}";
  } elsif (${action} eq 'dir') {
    ${HREF} .= "cur_url=${value}";
  }
  # DISPLAY MODE PARAM
  if (${action} ne 'pic' && ${action} ne 'dir') { #for 'pic' and 'dir' we have pre-defined display modes so they are excluded here
    if (${action} eq 'display_mode') {
      ${HREF} .= "${amp}display_mode=${value}";
    } else {
      ${HREF} .= "${amp}display_mode=$STATE{'display_mode'}"; #persist the display mode
    }
  }

  return escapeURL($HREF);
}

# Returns true if file matches type specified.
#   isFileType("file name", "type")
sub isFileType {
  my ($name, $type) = @_;
  return ($file_types{$name} eq $type) ? 1 : 0;
}

# Returns an html formatted list of depth path elements.
#   getDepthPath()
sub getDepthPath {
  my @directories = split('/', $STATE{'web_dir'});
  my $last_directory = pop @directories;
  my $depth_path = '<li><a href="/">home</a></li>';

  foreach my ${path} (@directories) {
    if (${path} ne '/') {
      $STATE{'web_dir'} =~ m:(^/${path}/|^/.+/${path}/):;
      if (${1} ne '') {
        my $itemTitle = getNiceFilename(${path});
        $depth_path .= '
      <li><a href="'.getHREF('dir',${1}).'">'.${itemTitle}.'</a></li>';
      }
    } else {
      # Not sure what this is for...
      $depth_path .= '@';
    }
  }

  # Append the collection head:
  $depth_path .= '<li class="depth-path-header"><h1>'.getNiceFilename($last_directory).'</h1></li>';

  # Append the collection description:
  # Consider replacing with current picture name + desc for SINGLE mode here.
  if ("$STATE{'page_description'}") {
    $depth_path .= '<li class="depth-path-header"><h2>'.$STATE{'page_description'}.'</h2></li>';
  }

  return $depth_path;
}

# Returns a linked image tag representing the file provided by $file_name
#   getIcon("name of file")
sub getIcon {
  my ($file_name) = @_;
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
    my ${static_thumbnail_path} = $STATE{'server_dir'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
    #Use built-in icon
         if (isFileType(${file_name},'folder')) { ${icon_file} = ${icon_folder};
    } elsif (isFileType(${file_name},'doc')) {    ${icon_file} = ${icon_doc};
    } elsif (isFileType(${file_name},'music')) {  ${icon_file} = ${icon_music};
    } elsif (-e ${static_thumbnail_path}) {       ${icon_file} = $STATE{'web_dir'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
    } else {                                      ${icon_file} = ${icon_unknown};
    }
    ${link_content} = "<img src=\"${icon_file}\" alt=\"${desc}\">";
  }
  return getLinkTag(${file_name},${link_content},${desc},${class});
}

# Returns an <a> tag containing appropriate href based on the type of file, state, etc.
#   getLinkTag("name of file", "link content", "file description", "CSS class name")
sub getLinkTag {
  my ($file_name, $link_content, $desc, $class) = @_;
  my ${link_tag};
  if (! "${desc}") {
    ${desc} = ${file_name};
    ${desc} .= ($file_descriptions{${file_name}} ne '') ? ' - '.stripHTML($file_descriptions{${file_name}}) : '';
  }
  if (isFileType(${file_name},'folder')) {
    #Folder
    ${link_tag} = "<a href=\"".getHREF('dir',"$STATE{'web_dir'}${file_name}")."\" class=\"${class}\" title=\"${desc}\">${link_content}</a>\n";
  } elsif (isFileType(${file_name},'pic')) {
    #Image
    ${link_tag} = "<a href='".getHREF('pic',${file_name})."' class='${class}' title='${desc}'>".${link_content}.'</a>';
  } else {
    # Music, text or other.  Just link to the file
    ${link_tag} = "<a href='$STATE{'web_dir'}${file_name}' class='${class}' title='${desc}'>${link_content}</a>\n";
  }
  return ${link_tag};
}

# Returns one of the nav buttons which change the mode.
# TODO: do this in javascript?
#   getNavButton("mode", "value", "text description")
sub getNavButton {
  my ($mode, $value, $desc) = @_;
  my ${toggle} = (${value} eq $STATE{'display_mode'}) ? 'on' : 'off';
  my ${icon_modifier} = lc(${value}); # Lowercase
  my ${href} = getHREF(${mode} , ${value});
  my ${img} = "<img src='${assets_root}/icon_button_${icon_modifier}.png' alt='${desc}'>";
  my ${linked_img} = "<a href='${href}' rel='nofollow' title='${desc}' id='button-${icon_modifier}'>${img}</a>";

  if ($STATE{'display_mode'} eq ${value}) {
    return ${img};
  } else {
    return ${linked_img};
  }
}

# Dump out the simple image list & create thumbnails as needed - main loop
#   commandLineMakeThumbs()
sub commandLineMakeThumbs {
  foreach my ${image_name} (@image_array) {
    my ${image_source} = $STATE{'server_dir'}.${image_name};
    print "  + ${image_source} : ";
    # Create small and large thumbnails as needed
    foreach my ${size} ('small', 'large') {
      my ${image_thumb_name} = $IMAGE_GLOBAL{'prefix_'.$size}.${image_name}.$STATE{'thumb_ext_cur'};
      my ${image_thumb} = $STATE{'server_dir'}.${image_thumb_name}; #This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
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

# Convert bytes into nice number for humans.
#   getFormattedFileSize(bytes)
sub getFormattedFileSize {
  my ($bytes) = @_;
  my ${file_size};
  if (${bytes} > 10000000) {
    ${file_size} = int(${bytes} / 1048576) . '&nbsp;MB';
  } elsif (${bytes} > 1000000) {
    ${file_size} = sprintf("%.1f", (${bytes} / 1048576)) . '&nbsp;MB';
  } elsif (${bytes} > 2047){
    ${file_size} = int(${bytes} / 1024) . '&nbsp;KB';
  } elsif (${bytes} > 1023){
    ${file_size} = sprintf("%.1f", (${bytes} / 1024)) . '&nbsp;KB';
  } elsif (${bytes} > 0){
    ${file_size} = ${bytes} . '&nbsp;B';
  } else {
    ${file_size} = '0&nbsp;B';
  }
  return ${file_size};
}


# Dump out the html formatted dir list - main loop
# TODO: Rename to getFiles()
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
      @file_info = stat $STATE{'server_dir'}.${file_name};
      #ALL THIS ISDIR SHOULD GO IN THE CACHE FILE!  ALSO NEED TO BE ABLE TO DELETE / RECACHE WITHOUT LOOSING INFO
      # Not used anymoer... ${is_dir} = S_ISDIR(${file_info[2]});
      if ($STATE{'display_mode'} eq 'LIST') {
        #@time_info = localtime ${file_info[9]};
        #EXTRACT FILE INFO FROM ARRAY AND PAD
        #${year} = ${time_info[5]} + 1900;
        #${month} = (qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec)) [(${time_info[4]})];
        #${minute} = (${time_info[1]} < 10) ? "0".${time_info[1]} : ${time_info[1]};
        #${day} = (${time_info[3]} < 10) ? "0".${time_info[3]} : ${time_info[3]};
        #${hour} = (${time_info[2]} < 10) ? "0".${time_info[2]} : ${time_info[2]};
        if ( ! isFileType(${file_name},'folder')) {
          ${file_size} = getFormattedFileSize(${file_info[7]});
        }
        print "
        <tr>
          <td class='col-picture'>";
            #GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
            print getIcon(${file_name});
            print "</td>
          <td class='col-description'>";
            #date isn't really used, but maybe in future?
            #my ${date} = "${day}-${month}-${year} ${hour}:${minute}";
            print getLinkTag(${file_name}, getParsedFileName(${file_name}), '', 'simple');
            if ($file_descriptions{${file_name}}) {
              print "<span class='file-description'>$file_descriptions{${file_name}}</span>";
            }
          print "</td>
          <td class='col-size'>${file_size}&nbsp;&nbsp;</td>
        </tr>";
      } elsif ($STATE{'display_mode'} eq 'THUMBS') {
        #GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
        # TODO: Use list just like slideshow.
        print '<table class="picture-icon-container" cellpadding="0" cellspacing="1"><tr><td valign="middle" align="center">';
        print getIcon(${file_name});
        print '</td></tr><tr><td valign="top" class="picture-icon-file-name" align="center">'.getParsedFileName(${file_name}).'</td></tr></table>';
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

      print '
      <h3>
        <strong>'.getParsedFileName(${file_name}).'</strong>';

        if ($file_descriptions{${file_name}}) {
          print "
            <span>$file_descriptions{${file_name}}</span>
          ";
        }

      print "
      </h3>

      <a class='picture-link previous' title='Previous image' href='".getHREF('pic',$STATE{'pic_previous_file'})."'>
        <img src='$STATE{'web_dir'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_previous_file'}$IMAGE_GLOBAL{'thumb_ext'}' data-src='$STATE{'web_dir'}$STATE{'pic_previous_file'}' alt='' id='PREVIOUS'>
      </a>
      <a class='picture-link large-picture-wrapper' href='".getHREF('display_mode','SLIDESHOW')."' title='Slideshow...'>"
        .getImageTag(${file_name},'')."
      </a>
      <a class='picture-link next' title='Next image' href='".getHREF('pic',$STATE{'pic_next_file'})."'>
        <img src='$STATE{'web_dir'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_next_file'}$IMAGE_GLOBAL{'thumb_ext'}' data-src='$STATE{'web_dir'}$STATE{'pic_next_file'}' alt='' id='NEXT'>
      </a>
      ";
    }
  } elsif ($STATE{'display_mode'} eq 'SLIDESHOW') {
    # SLIDESHOW IMAGE MODE
    # TODO: Use this for LIST|THUMBS|SLIDESHOW ########################################################################
    print '<ul id="files">';
    # Make sure large thumbs exist
    ${file_name} = $STATE{'pic_cur_file'};
    if (${file_name}) {
      foreach ${file_name} (@dir_list) {
        ${file_size} = '';
        @file_info = stat $STATE{'server_dir'}.${file_name};
        #ALL THIS ISDIR SHOULD GO IN THE CACHE FILE!  ALSO NEED TO BE ABLE TO DELETE / RECACHE WITHOUT LOOSING INFO
        # Not used anymore... ${is_dir} = S_ISDIR(${file_info[2]});

        #@time_info = localtime ${file_info[9]};
        #EXTRACT FILE INFO FROM ARRAY AND PAD
        #${year} = ${time_info[5]} + 1900;
        #${month} = (qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec)) [(${time_info[4]})];
        #${minute} = (${time_info[1]} < 10) ? "0".${time_info[1]} : ${time_info[1]};
        #${day} = (${time_info[3]} < 10) ? "0".${time_info[3]} : ${time_info[3]};
        #${hour} = (${time_info[2]} < 10) ? "0".${time_info[2]} : ${time_info[2]};
        if ( ! isFileType(${file_name}, 'folder')) {
          ${file_size} = getFormattedFileSize(${file_info[7]});
        }

        my $is_selected = ($STATE{'pic_cur_file'} eq $file_name) ? '1' : '0';
        my $file_type = $file_types{${file_name}};

        # TODO: data-width and data-height
        print '
        <li>
          <a href="'.$STATE{'web_dir'}.${file_name}.'" class="filename" data-selected="'.${is_selected}.'" data-file-type="'.${file_type}.'" data-size="'.${file_size}.'">'
          .getParsedFileName(${file_name})
          .'</a>
          <div>'.$file_descriptions{$file_name}.'</div>
        </li>
        ';
      }

      print '
      </ul>
      ';
    }
  }
}


# Determines the page context, settings, etc. based on the current url.
#   calculateImageListState()
sub calculateImageListState {
  if (@image_array > 0) {
    $STATE{'pic_last_idx'}         = $#{image_array};
    $STATE{'pic_array_length'}     = $STATE{'pic_last_idx'} + 1;
    if ($STATE{'pic_cur_file'}){
      if ( "$image_hash{ $STATE{'pic_cur_file'} }" ne '' ){
        $STATE{'pic_cur_idx'} = $image_hash{ $STATE{'pic_cur_file'} };
      } else {
        $ERROR = 1;
        $DUMP .= "DID NOT FIND '$STATE{'pic_cur_file'}' IN THE LIST!<br>";
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
  # Would be ideal if we didn't un-encode then re-encode the url_encoded.  In many cases, $ENV{REQUEST_URI} has what we need!
  # Problem is that there are several ways to get the 'url' (cur_url or directly from path if no mod_re-write)
  $STATE{'web_dir_encoded'} = $STATE{'web_dir'};
  $STATE{'web_dir_encoded'} =~ s/ /%20/g;
  $STATE{'page_description'} = stripHTML(getSitemapData('pageDescription'));
}

# GET READY TO PARTY!
calculateImageListState();

if (${COMMANDLINE}) {
  # print "display_mode : $STATE{'display_mode'}\n";
  commandLineMakeThumbs();
  print "[done]\n";
  exit 0;
}

# RENDER HTML HEAD #############################################################
print "Content-type: text/html\n\n";
print '<!DOCTYPE html>
<html class="jcd">
  <head>
    <script>
      (function(H){H.className=H.className.replace(/\bjcd\b/,"jcd-js")})(document.documentElement)
    </script>
    <meta charset="utf-8">
    <meta content="initial-scale=1, minimum-scale=1, width=device-width" name="viewport">
    <title>'.$STATE{'title'}.'</title>
    <meta name="description" content="'.$STATE{'page_description'}.'">
    <link href="'.${assets_root}.'/jcdsee.css" rel="stylesheet" type="text/css">
    <!--[if lt IE 8]><script src="http://ie7-js.googlecode.com/svn/version/2.1(beta4)/IE8.js"></script><![endif]-->
';

if ($STATE{'test_mode'}) {
  # Make it pink if in test mode.
  print "<style type='text/css'> body {outline: 1px solid red;background-color: pink;} </style>";
}

print '
  </head>
  <body id="mode-'.lc($STATE{'display_mode'}).'" data-adminurl="'.${assets_root}.'/admin/index.cgi?display_url&cur_url='.$STATE{'web_dir'}.'">

    <div id="nav">
      <ul id="depth-path">'
        .getDepthPath().'
      </ul>
      <div id="mode-buttons">'
        .getNavButton("display_mode","LIST","LIST MODE")
        .getNavButton("display_mode","THUMBS","THUMBNAIL IMAGE MODE")
        .getNavButton("display_mode","SINGLE","SINGLE IMAGE MODE")
        .getNavButton("display_mode","SLIDESHOW","SLIDESHOW DISPLAY MODE")
        .'
      </div>
    </div>

    <div id="content">
      <div>';
        # Show warning if trying to access slideshow without JS.
        if ($STATE{'display_mode'} eq 'SLIDESHOW') {
          print '
          <noscript>
            <h1>JavaScript is disabled</h1>
            <h2>Sorry, the slideshow function requires JavaScript. Please choose a different display mode from the top-right corner or wait and this page will be redirected in 10 seconds.</h2>
            <meta http-equiv="refresh" content="10; url='.getHREF('display_mode', 'SINGLE').'">
          </noscript>
          ';
        }

        # TODO: Use slideshow list instead of this table.
        if ($STATE{'display_mode'} eq 'LIST') {
          print '
          <table id="file_list" cellpadding="4" cellspacing="0" border="0">';
        }
        # Render the file list.
        dumpDirList();
        # Finish table for LIST mode.
        if ($STATE{'display_mode'} eq 'LIST') {
          print '
          </table>
          ';
        }

        print '
        <!-- close #content div -->
      </div>
    </div>
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
    -->';
    # Debug & error information.
    if (${ERROR} || $STATE{'test_mode'}) {
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
        <div style='margin-top:11px;border:2px solid red;background-color:#f99;font-size:9px;font-family:verdana,sans-serif;color:#a00;'>
          <b style='font-size:10px;color:black;'>ERROR:</b><br>
          <pre>${DUMP}</pre>
        </div>";
    }

    $TIMER{'total_e'} = gettimeofday();
    $TIMER{'total'} = sprintf("%.3f", ($TIMER{'total_e'} - $TIMER{'total_s'}));

    print '
    <div id="footer">
      <a id="copyleft" rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank">
        <img alt="Creative Commons License" src="'.${icon_copyleft}.'">
      </a>
      <div id="usage">
        <a href="https://github.com/jonathancross/pics.jonathancross.com" title="See the latest source code behind this website.">JCDSee '.${VERSION}.'</a><br>
        Script executed in: '.$TIMER{'total'}.' seconds.';
        if ($STATE{'country_code'}) {
          print " Geo: $ENV{'HTTP_CF_IPCOUNTRY'}";
        }
        print '<br>'
        .getSitemapData('pageDate')
        .getSitemapData('pageSize')
        .'
      </div>
    </div>

    <script src="'.${assets_root}.'/jcdsee.js"></script>
  </body>
</html>
';
