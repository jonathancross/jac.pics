#!/usr/bin/perl
#
# JCDSee by Jonathan Cross : www.JonathanCross.com
# See GitHub for license, usage, examples and more info:
#  • https://github.com/jonathancross/pics.jonathancross.com
# TODO: Update
#   file_descriptions
#   dir_list
#   file_types
#   image_array
#   image_hash
################################################################################

use strict;
use warnings;
use Image::Magick;
use CGI ':standard';
use CGI::Carp 'fatalsToBrowser';
use Fcntl ':mode';
use Time::HiRes 'gettimeofday';
use XML::LibXSLT;
use XML::LibXML;

my %TIMER;
$TIMER{'total_s'} = gettimeofday();

# Command line execution / debugging.
my ${COMMANDLINE} = 0;
if ( defined($ARGV[0]) && ($ARGV[0] eq 'debug') ) {
  ${COMMANDLINE} = 1;
  print "\nDEBUG MODE\n\n";
}

# Load software version number from external file.
open FILE, 'VERSION';
my $VERSION = <FILE>;
close FILE;

# GLOBAL VARIABLES #############################################################
# DIRECTORY LIST ARRAYS
my(
  @dir_list,          # List of files as loaded from database (not just images).
  @image_array,       # Array of images (full path starting with /pics/)
  %image_hash,        # Hash of each image pointing to its index in @image_array
  %file_descriptions, # Optional html descriptions of each file.
  %file_dirs,         # Stores the directory (path) of each file.
  %file_dirs_encoded, # Stores the directory (path) of each file, URL encoded.
  %file_types         # Type of the given file.
);
my ${ROOT} = (${COMMANDLINE}) ? '.' : $ENV{DOCUMENT_ROOT};
my ${PICS} = '/pics';
my ${ASSETS} = '/jcdsee'; # Folder containing assets used by this script. (icons, buttons, css, etc)
my ${JCDSEE_SCRIPT} = 'jcdsee.cgi'; # Name of the stub script, we need this so we don't show it in the dir listing.
my ${DATABASE_FILENAME} = '.jcdsee'; # Filename used for each folder's database.
my ${TEST_SUBDOMAIN_STRING} = 'test'; # Special test mode staging url
my ${TITLE_SEPARATOR} = ' : ';
my $XML_SITEMAP_FILE = "${ROOT}/sitemap.xml";
my $XSL_SITEMAP_FILE = "${ROOT}${ASSETS}/jcdsee.xsl";
my %SITEMAP_DATA = getSitemapData();

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
  max_width         => 0,      # Max width placeholder
  max_height        => 0       # Max height placeholder
);

# DISPLAY STATE VARS
my %STATE = (
  canonical_url     => '', # Full URL, escaped with display_mode.
  country_code      => $ENV{'HTTP_CF_IPCOUNTRY'},
  cur_dir_name      => '', # Will have only the name of the current directory (no slashes)
  database_file     => '', # Full server path to the .jcdsee database file.
  display_mode      => '', # Display mode (single|list|thumb|slide) Default=list
  error_msg         => '', # Error message indicating app is in an error state.
  go_param          => '', # Sanitized `go` param - will be a url identifier
  go_redirect_url   => '', # Url matching `go_param` from sitemap (if found).
  is_default        => 1,  # A boolean to tell us if all the display settings are at default.
  is_deprecated_param => 0,  # Identifies requests using 'cur_url' or 'pic' params which are deprecated.
  page_description  => '', # Description of current page (from xml database)
  # pic_* used for current position in photo list
  pic_array_length  => 0,
  pic_cur_file      => '', # Filename of the currently selected image.
  pic_cur_idx       => 0,
  pic_cur_number    => 0,
  pic_last_idx      => 0,
  pic_next_file     => '',
  pic_next_idx      => 0,
  pic_previous_file => '',
  pic_previous_idx  => 0,
  prefix_cur        => '', # Will hold the current prefix (prefix_small or prefix_large)
  protocol          => 'http://', # TODO: generate this.
  server_dir        => '', # Full server path to the folder being listed.
  server_name       => $ENV{SERVER_NAME},
  test_mode         => 0,  # Test mode (0 or 1) Default=0
  thumb_ext_cur     => '', # Will hold the current extension (thumbnail pics are always jpg for example)
  title             => 'Jonathan Cross', # Document title base
  web_dir           => '', # Directory path from the document root eg: /pics/foo bar/
  web_dir_encoded   => '', # URL encoded version of `web_dir`, eg:     /pics/foo%20bar/
  web_full_path_clean => '' # Full web path to the current image eg:   /pics/foo bar/default.jpg Can also point to default image (if available) or web_dir.  Does not include display_mode.
);
my %DEFAULTS = (
  display_mode      => 'list',
  test_mode         => 0,
);
my %LEGACY_MODES = (
  LIST      => 'list',
  THUMBS    => 'thumb',
  SINGLE    => 'single',
  SLIDESHOW => 'slide'
);

# Look for `go` param, but ignore if it contains odd chars.
if (param('go') && param('go') =~ m:^([A-Za-z0-9/_.-]+)$:) {
  $STATE{'go_param'} = $1;
  $STATE{'go_redirect_url'} = getSitemapGoUrl($STATE{'go_param'});
  # Redirect to URL identified by the `go` param.
  print redirect(-status => 302, -url => $STATE{'go_redirect_url'});
  exit;
}

# LOAD / SET PARAMS & DEFAULTS
$STATE{'display_mode'} = convertFromLegacyDisplayMode(param('display_mode'));
$STATE{'test_mode'} = ($ENV{SERVER_NAME} =~ /^${TEST_SUBDOMAIN_STRING}/) ? 1 : 0;

# CURRENT URL FROM PARAM -OR- PATH

# Deprecated old params: 'cur_url' and 'pic'.
# TODO: Remove all this code in a month or two.
if (param('cur_url') || param('pic')) {
  $STATE{'is_deprecated_param'} = 1;
  # ERROR: there should be no way to send these params anymore (see .htaccess)
  #        but just put this here in case.
  $STATE{'error_msg'} = 'This file or folder is now gone.';
}

# Path to the folder or a picture in a folder.
if (param('pic_path') && (param('pic_path') =~ m:(.*/)(.*):) ) {
  $STATE{'is_deprecated_param'} = 0;
  $STATE{'web_dir'} = $1;
  # Old code would add trailing slash if needed, but I think unnecessary now.
  # $STATE{'web_dir'} =~ s:[^/]$:$&\/:;
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
  $STATE{'web_dir'} = (${ARGV[1]}) ? ${ARGV[1]} : "${ROOT}${PICS}"; # have dir default to "." for commandline debugging
  $STATE{'server_dir'} = $STATE{'web_dir'};
  $STATE{'display_mode'} = ${ARGV[2]};
  $STATE{'pic_cur_idx'} = int(${ARGV[3]});
} elsif ($STATE{'web_dir'} =~ m:^/: && $STATE{'web_dir'} !~ m:/[.][.]: && -d $ENV{DOCUMENT_ROOT}.$STATE{'web_dir'}){ # Have to validate the directory for security reasons
  $STATE{'server_dir'} = $ENV{DOCUMENT_ROOT}.$STATE{'web_dir'};
  $STATE{'cur_dir_name'} = $STATE{'web_dir'};
  $STATE{'cur_dir_name'} =~ s:^.*/([^/]+)/:$1:; # Get last dir name from the url and remove all slashes.
} else {
  # ERROR
  $STATE{'error_msg'} = 'Directory not found.';
}

$STATE{'database_file'} = $STATE{'server_dir'}.${DATABASE_FILENAME};

# Load  / Build the list of files.
loadFileDatabase();

# Default pic_cur_file to first image if one exists. Fixes issue #17.
if (! $STATE{'pic_cur_file'} && @image_array) {
  $STATE{'pic_cur_file'} = $image_array[0];
}

$STATE{'web_full_path_clean'} = $STATE{'web_dir'}.$STATE{'pic_cur_file'};

$STATE{'title'} = getCurrentPageTitle($STATE{'web_dir'}); # Figure out the title of the page

# Figure out if all settings are same as the default.
while ((my $key, my $value) = each(%DEFAULTS)) {
  if (${value} ne $STATE{$key}) {
    $STATE{'is_default'} = 0;
    last;
  }
}

# Display mode setup & defaults.
if (isMode('thumb')) {
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_large'}; # max height of large thumbnail, normally all will have same height
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_large'}; # max width of large thumbnail, normally never get this wide
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_large'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
} elsif (isMode('single|slide') && $STATE{'pic_cur_file'}) { # Only allow single|slide if there is 1 or more images.
  # Do not prefix image name, use full-size image
  $STATE{'prefix_cur'} = '';
  $STATE{'thumb_ext_cur'} = '';
} else {
  $STATE{'display_mode'} = 'list';
  $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_small'}; # max dimension of small thumbnail
  $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_small'}; # max dimension of small thumbnail
  $STATE{'prefix_cur'} = $IMAGE_GLOBAL{'prefix_small'};
  $STATE{'thumb_ext_cur'} = $IMAGE_GLOBAL{'thumb_ext'};
}

$STATE{'canonical_url'} = $STATE{'protocol'}.$STATE{'server_name'}.getHREF(); # Easiet way to get current escaped url.

my %ICON = (
  unknown => "${ASSETS}/icon_unknown$STATE{'prefix_cur'}png",
  folder => "${ASSETS}/icon_folder$STATE{'prefix_cur'}png",
  music => "${ASSETS}/icon_music$STATE{'prefix_cur'}png",
  doc => "${ASSETS}/icon_doc$STATE{'prefix_cur'}png",
  copyleft => "${ASSETS}/icon_copyleft.png",
);


# Builds image_array, image_hash, file_descriptions, file_types, and dir_list.
#   loadFileDatabase()
sub loadFileDatabase {
  my (@database_raw, @dir_list_raw, $file_name);
  # Create the database if it doesn't exist yet.
  if (! -e $STATE{'database_file'}) {
    createDatabase();
  }
  # Now that we have a database for sure, load in the data.
  # TODO: or $STATE{'error_msg'} = "Cant open file: '$STATE{'database_file'}'." && printHtmlHead;
  open(DATA, $STATE{'database_file'}) or die "Content-Type: text/html\n\nCant open file: \"$STATE{'database_file'}\".";
  @database_raw = <DATA>;
  close(DATA);
  # Process the database contents.
  my ${img_count} = 0;
  my ${file_count} = 0;
  # Slurp in file info.
  foreach my ${line} (@database_raw){
    chop(${line});
    # TODO: Allow first line to contain meta data?
    my($file, $description) = split(/[|]/, $line);
    # Skip blank lines and comment lines.
    if ($file eq '' || $file =~ /^#/) return;

    # Determine directory of each file (can now mix images from different folders).
    # TODO: remove hardcoded 'pics'.
    if ($file =~ @^/pics/@) {
      # Extract file_dir is needed because we need to do lots of file name parsing.
      ($file_dirs{$file}, $file_name) =~ m@^(.*/)(.*)@;
    } elsif ($file =~ @^[^/]+$@) {
      # Normal file in current folder
      $file_name = $file;
      $file = $STATE{'web_dir'}.$file;
      $file_dirs{$file} = $STATE{'web_dir'};
    } else {
      $STATE{'error_msg'} = "Could not parse local or absolute file path: ${file}";
      $file_name = $file;
    }
    $file_dirs_encoded{$file} = urlEscapeSpaces($file_dirs{$file});

    # Identify type of the file or folder
    if ($file_name =~ /[.](jp[e]?g|gif|png)$/i) {
      # Picture
      $image_array[$img_count] = $file;
      $image_hash{$file} = $img_count;
      $file_types{$file} = 'pic';
      ${img_count}++;
    } elsif (-d ${ROOT}.${file}) {
      # Folder
      $file_types{$file} = 'folder';
    } elsif ($file_name =~ /[.]mp3$|[.]wav$|[.]as[xf]$|[.]wm[a]$|[.]m3u$|[.]m[io]d$|[.]aif+$/i) {
      # Music (.mpeg,mpg,mp4,mp3,mp2,mp1,wav,asx,asf,wmx,wma,m3u,mid,mod,aif,aiff,qt)
      $file_types{$file} = 'music';
    # } elsif ($file_name =~ /[.](mp[e]?g|avi|mov|flv|wmv|qt)$/i) {
    # Video (.mpeg,mpg,avi,mov,flv,wmv,qt)
    # $file_types{$file} = 'video';
    } elsif ($file_name =~ /[.](pdf|doc|htm[l]?|txt|nfo|css|js)$/i) {
      # Text Document (pdf,doc,txt,htm,html,nfo,css,js)
      $file_types{$file} = 'doc';
    } else {
      # Unknown file
      $file_types{$file} = 'unknown';
    }
    $dir_list[$file_count] = $file;
    $file_descriptions{$file} = $description;
    $file_count++;
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
    if (${line} !~ /^[.]|${JCDSEE_SCRIPT}/) {
      print DATA "${line}|\n";
    }
  }
  close(DATA);
}

# Creates a thumbnail image.
#   createImageThumbnail("source", "destination thumb full path")
sub createImageThumbnail {
  my ($image_source, $image_thumb_path) = @_;
  my ${image_obj} = Image::Magick->new;
  my ${img_status} = ${image_obj}->Read(${image_source}); warn ${img_status} if ${img_status};
  ${img_status} = ${image_obj}->Flatten(); # for PSD files
  # Resize to make large thumbnails same height except in extremely wide images.  Small thumbs resize proportionally
  ${img_status} = ${image_obj}->Thumbnail(geometry=>"$IMAGE{'max_width'}x$IMAGE{'max_height'}", filter=>'Lanczos');
  # Cannot remove profile if $COMMANDLINE
  # ${img_status} = ${image_obj}->Profile(name=>undef); warn ${img_status} if ${img_status};
  # Set JPEG compression level for thumb
  ${img_status} = ${image_obj}->Set(compression=>'JPEG');
  ${img_status} = ${image_obj}->Set(quality=>$IMAGE_GLOBAL{'thumb_quality'});
  ${img_status} = ${image_obj}->Set(type=>'Optimize');
  ${img_status} = ${image_obj}->Write(${image_thumb_path}); warn ${img_status} if ${img_status};
  @${image_obj} = (); # Clear memory
}

# Returns an <img> tag. Will create thumbs if necessary.
#   getImageTag("file name without path", "prefix for image")
sub getImageTag {
  my ($image_name, $image_prefix) = @_;
  my ${image_thumb_name} = ${image_prefix}.${image_name}.$STATE{'thumb_ext_cur'};
  my ${image_thumb_path} = ${ROOT}.$file_dirs{$image_name}.${image_thumb_name}; # This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
  my ${image_thumb_url} = $file_dirs{$image_name}.${image_thumb_name}; # Image url for browser
  # Make a Thumbnail if necessary
  # Datestamp isn't really important so i'm removing test to speed up display in 99% of cases
  # if ( ! (-e ${image_thumb_path}) || (((stat(${image_source}))[9]) > ((stat(${image_thumb_path}))[9])) ) {
  if ($STATE{'prefix_cur'} && ! (-e ${image_thumb_path})) {
    # Make a thumbnail of the image
    my ${image_source} = $ROOT.$file_dirs{$image_name}.${image_name};
    createImageThumbnail(${image_source}, ${image_thumb_path});
  }
  $image_thumb_url = urlEscapeSpaces($image_thumb_url);
  my $alt = (isMode('thumb')) ? stripHTML($file_descriptions{${image_name}}) : '';
  return "<img src='${image_thumb_url}' class='picture-icon' alt='${alt}'>";
}

# Returns a clean SEO title for the current page which is reverse of path.
# Examples:
#  • /pics/2005/India/Sikkim/                   => Sikkim : India : 2005
#  • /pics/2005/India/Sikkim/        05_Nina_hat.jpg OR
#  • /pics/2005/India/Sikkim/2005-12-25_Nina_hat.jpg
#                                    => Nina hat : Sikkim : India : 2005
#   getCurrentPageTitle("path")
sub getCurrentPageTitle {
  my ($path) = @_;
  $path =~ s@${PICS}|\/$@@g; # Delete "/pics" root and trailing slash.
  $path =~ s@/@${TITLE_SEPARATOR}@g; # Replace all slashes with colon.
  if (isMode('single')) {
    $path .= ${TITLE_SEPARATOR}.getNiceFilename($STATE{'pic_cur_file'});
  }
  # Split the path elements, then reassemble in reverse:
  $path = join($TITLE_SEPARATOR, reverse(split($TITLE_SEPARATOR, $path)));
  $path .= $STATE{'title'};
  $path = getNiceFilename($path);
  return $path;
}

# Returns a string representing a filename made pretty for humans.
# Date prefix and file extention will be removed; dashes, underscorea and
# dots -._ will each be replaced with a blank space.
# Example: 2010-12-01_Texas-Man.eats_bbq.jpg => Texas Man eats bbq
#   getNiceFilename("filename")
sub getNiceFilename {
  my ($fn) = @_;
  $fn = removeDatePrefix($fn);
  $fn = removeNumberPrefix($fn);
  $fn = removeFileExtension($fn);
  $fn =~ s@[._-]@ @g;
  $fn =~ s@([[:lower:]])([[:upper:]\d])@$1 $2@g; # Space out camelCase words.
  return $fn;
}

# Returns a string representing a filename with date prefix removed.
# Example: 2010-12-01_Texas-Man.jpg => Texas-Man.jpg
#   removeDatePrefix("filename")
sub removeDatePrefix {
  my ($fn) = @_;
  $fn =~ s@(^| )\d\d\d\d-\d\d-\d\d_@$1@g; # Delete date prefixes
  return $fn;
}

# Returns a string representing a filename with numbered prefix removed.
# Example: 21_Texas-Man.jpg => Texas-Man.jpg
#   removeNumberPrefix("filename")
sub removeNumberPrefix {
  my ($fn) = @_;
  $fn =~ s:^\d+_(.+):$1:g; # Delete number prefixes when there is a filename
  return $fn;
}

# Returns a string representing a filename with the file extension removed.
# Example: 2010-12-01_Texas-Man.jpg => 2010-12-01_Texas-Man
#   removeFileExtension("filename")
sub removeFileExtension {
  my ($fn) = @_;
  $fn =~ s:[.][A-Za-z]{3}$::g; # Delete 3-letter file extensions
  return $fn;
}

# Returns a hash containing the parsed XML and XSL used for the sitemap data.
#   getSitemapData()
sub getSitemapData {
  my $XMLparser = XML::LibXML->new();
  my $XSLparser = XML::LibXSLT->new();
  (-f $XML_SITEMAP_FILE) or return "Lost XML: $XML_SITEMAP_FILE";
  (-f $XSL_SITEMAP_FILE) or return "Lost XSL: $XSL_SITEMAP_FILE";

  my %sitemapData = (
    xml => $XMLparser->parse_file($XML_SITEMAP_FILE),
    xsl => $XSLparser->parse_stylesheet_file($XSL_SITEMAP_FILE)
  );
  return %sitemapData;
}

# Returns a single string data item from the sitemap XML database.
# Data item can be one of these three types: pageDescription|pageDate|pageSize
# or urlFragment.  If type is 'urlFragment', you must send the fragment as the
# second parameter to this function.
#   getSitemapDataItem("databaseItem", "urlFragment"?)
sub getSitemapDataItem {
  my ($item, $url) = @_;
  $url = $url || $STATE{'web_dir_encoded'};
  my $results = $SITEMAP_DATA{'xsl'}->transform(
    $SITEMAP_DATA{'xml'},
    DATA_ITEM => "'$item'",
    URL => "'$url'"
  );
  my $string = $SITEMAP_DATA{'xsl'}->output_as_chars($results);
  chomp($string);
  return $string;
}

# Returns URL from the sitemap XML database which best matches the $goParam.
#   getSitemapGoUrl("goParam")
sub getSitemapGoUrl {
  my ($goParam) = @_;
  # All possible matches from sitemap starting from most recent (reverse).
  my @urls = reverse split('\n', getSitemapDataItem('urlFragment', $goParam));

  # Select best/first URL (case incensitive) which matches the folder name.
  # Exact match, usually a year.
  # Example: pics/2015/
  my ($perfectMatchURL) = grep { m@.+/$goParam/$@i } @urls;

  # While ignoring date prefix, get matching URL suffix.
  # Example: "india" matches pics/2006/2006-12-10_India/
  my ($datelessURL) = grep { m@.+\d\d\d\d-\d\d-\d\d_$goParam/$@i } @urls;

  # Select URL containing term anywhere in folder name.
  # Example: "zb" matches pics/FoozBall/
  my ($similarURL) = grep { m@.+/[^/]*$goParam[^/]*/$@i } @urls;

  # Return best match first or the error page:
  return $perfectMatchURL
      || $datelessURL
      || $similarURL
      || ${urls[0]}
      || '/error';
}

# Returns an html formatted string representing the filename passed in.
#   getParsedFileName("file name to be parsed")
sub getParsedFileName {
  my ($file_name) = @_;
  my ${strip_date} = isMode('thumb|single|slide');
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

# Returns a string with HTMl tags removed and quotes encoded (used by alt tags).
#   stripHTML("string")
sub stripHTML {
  my ($string) = @_;
  ${string} =~ s/<[^>]+>//g;
  ${string} =~ s/"/&quot;/g; # quotes: "
  ${string} =~ s/'/&#39;/g; # apos: '
  return ${string};
}

# Returns a URL with spaces escaped.
#   urlEscapeSpaces('url')
sub urlEscapeSpaces {
  my ($url) = @_;
  $url =~ s: :%20:g;
  return $url;
}


# Returns the new display mode name that corresponds to the legacy mode name.
# Will just return the mode if it is not legacy.
# TODO: Cleanup after we have 301 redirects in place for the old URLs and Google has a chance to reindex the site.
#   convertFromLegacyDisplayMode('legacy-mode')
sub convertFromLegacyDisplayMode {
  my ($mode) = @_;
  my $legacyMode = $LEGACY_MODES{$mode};
  if ($legacyMode) {
    return $legacyMode;
  }
  return $mode;
}

# Returns true if the given display_mode equals the current $STATE{'display_mode'}.
#   isMode('display_mode')
sub isMode {
  my ($mode) = @_;
  $mode = qr/$mode/;
  return ($STATE{'display_mode'} =~ /^$mode$/);
}

# Builds a custom HREF given the object you want to link to.

#   OLDgetHREF(action[pic|dir|display_mode],  value[pic=url|dir=folder_name|display_mode])
sub OLDgetHREF {
  my ($action, $value) = @_;

  # display_mode
  #   dir          = norm
  #   pic          = do not use
  #   display_mode = use supplied
  # ---------------------------------------
  # *norm = use if not default.

  my ${HREF};
  # my $local_path = (${action} eq 'dir') ? ${value} : $STATE{'web_dir'} ;
  if (${action} eq 'dir') {
    # Special case for dir: we can ignore display_mode setting.
    ${HREF} = "${value}";
    return ${HREF};
  } elsif (${action} eq 'dispaly_mode' && ${value} eq $DEFAULTS{'display_mode'}) {
    # Special case when button turns it into the default
    ${HREF} = "$STATE{'web_dir'}";
    return ${HREF};
  } else {
    ${HREF} = "/${JCDSEE_SCRIPT}?";
  }
  # SET URL PARAM
  if (${action} eq 'pic') {
    ${HREF} .= "pic_path=$STATE{'web_dir'}${value}";
  } elsif (${action} eq 'display_mode') {
    ${HREF} .= "pic_path=$STATE{'web_full_path_clean'}";
  } elsif (${action} eq 'dir') {
    ${HREF} .= "pic_path=${value}";
  }
  # DISPLAY MODE PARAM
  if (${action} ne 'pic' && ${action} ne 'dir') { # for 'pic' and 'dir' we have pre-defined display modes so they are excluded here
    if (${action} eq 'display_mode') {
      ${HREF} .= "&amp;display_mode=${value}";
    } else {
      ${HREF} .= "&amp;display_mode=$STATE{'display_mode'}"; # persist the display mode
    }
  }

  return urlEscapeSpaces($HREF);
}

# Builds a custom HREF given the object you want to link to.
# If you don't supply a path, it will link to current file / path.
# If you don't supply a display mode, it will use the current mode.
#   getHREF("path (file or folder)", "display_mode")
sub getHREF {
  my ($path, $display_mode) = @_;
  $path ||= $STATE{'web_full_path_clean'};
  $path =~ s:^/::; # Remove leading slash to normalize.
  $display_mode ||= $STATE{'display_mode'};
  $display_mode = convertFromLegacyDisplayMode($display_mode);
  my ${href} = "/${display_mode}/${path}";
  return urlEscapeSpaces(${href});
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
  my $last_directory = getNiceFilename(pop @directories);
  my $new_display_mode = isMode('single|slide') ? $DEFAULTS{'display_mode'} : $STATE{'display_mode'};
  my $depth_path = '<li><a href="/">home</a></li>';

  foreach my $path (@directories) {
    if ($path ne '/') {
      $STATE{'web_dir'} =~ m:(^/$path/|^/.+/$path/):;
      if ($1) {
        my $itemTitle = getNiceFilename($path);
        $depth_path .= '
      <li><a href="'.getHREF($1, $new_display_mode).'"
             data-old-href="'.OLDgetHREF('dir', $1).'"
             >'.${itemTitle}.'</a></li>';
      }
    } else {
      # Not sure what this is for...
      $depth_path .= '@';
    }
  }

  # Link collection head if not in list or thumb mode.
  if (! isMode('list|thumb')) {
    $last_directory = '<a href="'.getHREF('', $new_display_mode).'" title="Back to all files.">'.$last_directory.'</a>';
  }

  # Append the collection head:
  $depth_path .= '<li class="depth-path-header"><h1>'.$last_directory.'</h1></li>';

  # Append the collection description:
  # Consider replacing with current picture name + desc for single mode here.
  if ("$STATE{'page_description'}") {
    $depth_path .= '<li class="depth-path-header"><h2>'.$STATE{'page_description'}.'</h2></li>';
  }

  return $depth_path;
}

# Returns a linked image tag representing the file provided by $file_name.
# TODO: Rename file_name to just "file" because it has full path.
#   getIcon("file name")
sub getIcon {
  my ($file_name) = @_;
  my ${link_content};
  my ${class} = '';
  my ${desc} = ${file_name};
  ${desc} .= ($file_descriptions{${file_name}})? ' - '.stripHTML($file_descriptions{${file_name}}) : '';
  if (isFileType(${file_name}, 'pic')) {
    # Image icon.
    ${class} = ($STATE{'pic_cur_file'} eq ${file_name}) ? 'current_pic' : 'pic' ;
    ${link_content} = getImageTag(${file_name}, $STATE{'prefix_cur'});
  } else {
    # Static icon file or built-in icon.
    my ${icon_file} = getStaticIcon(${file_name});
    ${link_content} = "<img src=\"${icon_file}\" alt=\"${desc}\">";
  }
  return getLinkTag(${file_name},${link_content},${desc},${class});
}

# Returns the path of a static icon for $file_name.
#   getStaticIcon("file name")
sub getStaticIcon {
  my ($file_name) = @_;
  my ${icon_file};
  # We can create and upload a static thumbnail icon for any filetype... will replace default question mark
  my ${static_thumbnail_path} = $ROOT.$file_dirs{$image_name}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
  # Use built-in icon
       if (isFileType(${file_name}, 'folder')) { ${icon_file} = $ICON{'folder'};
  } elsif (isFileType(${file_name}, 'doc')) {    ${icon_file} = $ICON{'doc'};
  } elsif (isFileType(${file_name}, 'music')) {  ${icon_file} = $ICON{'music'};
  } elsif (-e ${static_thumbnail_path}) {        ${icon_file} = $STATE{'web_dir'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
  } else {                                       ${icon_file} = $ICON{'unknown'};
  }
  # Could do this in loop, but it checks filesystem for static version of every icon!
  # foreach my ${type} ('folder', 'doc', 'music', 'unknown') {
  #   if (isFileType(${file_name}, ${type})) {
  #     ${icon_file} = $ICON{$type};
  #     last;
  #   }
  # }
  # # Found static image icon?  Then use it instead:
  # if (-e ${static_thumbnail_path}) {
  #   ${icon_file} = $STATE{'web_dir'}.$STATE{'prefix_cur'}.${file_name}.$STATE{'thumb_ext_cur'};
  # }
  return ${icon_file};
}

# Returns an <a> tag containing appropriate href based on the type of file, state, etc.
# TODO: Rename file_name to just "file" because it has full path.
#   getLinkTag("full file with path", "link content", "file description", "CSS class name")
sub getLinkTag {
  my ($file_name, $link_content, $desc, $class) = @_;
  my ${link_tag};
  if (! ${desc}) {
    ${desc} = ${file_name};
    ${desc} .= ($file_descriptions{${file_name}} ne '') ? ' - '.stripHTML($file_descriptions{${file_name}}) : '';
  }
  my $full_path = "$STATE{'web_dir'}${file_name}";
  if (isFileType(${file_name}, 'folder')) {
    # Folder
    ${link_tag} = "<a href=\"".getHREF(${full_path})."\"
                      data-old-href=\"".OLDgetHREF('dir', ${full_path})."\"
                      class=\"${class}\"
                      title=\"${desc}\"
                      >${link_content}</a>\n";
  } elsif (isFileType(${file_name}, 'pic')) {
    # Image
    ${link_tag} = "<a href='".getHREF(${full_path}, 'single')."'
                      data-old-href='".OLDgetHREF('pic', ${full_path})."'
                      class='${class}'
                      title='${desc}'
                      >".${link_content}.'</a>';
  } else {
    # Music, text or other = just link to the file directly.
    ${link_tag} = "<a href='${full_path}'
                      class='${class}'
                      title='${desc}'
                      >${link_content}</a>\n";
  }
  return ${link_tag};
}

# Returns one of the nav buttons which change the mode.
# TODO: do this in javascript?
#   getNavButton("mode", "value", "text description")
sub getNavButton {
  my ($mode, $value, $desc) = @_;
  my $icon_modifier = lc(${value}); # Lowercase
  my $href = getHREF('', $value);
  my $img = "<img src='${ASSETS}/icon_button_${icon_modifier}.png' alt='${desc}'>";
  my $linked_img = "<a href='${href}'
                       data-old-href='".OLDgetHREF(${mode}, ${value})."'
                       rel='nofollow'
                       id='button-${icon_modifier}'
                       >${img}</a>";
  if (isMode($value)) {
    return $img;
  } else {
    return $linked_img;
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
      my ${image_thumb_path} = $ROOT.${image_thumb_name}; #This holds the filename of the current image you will be reading and or writing.  Can be a small thumbnail, large thumbnail or full-size image.
      print " [${size} :";
      # Make a Thumbnail if necessary
      if (! -e ${image_thumb_path}) {
        # Manually inject the correct width and height
        $IMAGE{'max_width'} = $IMAGE_GLOBAL{'max_width_'.$size};
        $IMAGE{'max_height'} = $IMAGE_GLOBAL{'max_height_'.$size};
        # Make a thumbnail of the image
        createImageThumbnail(${image_source}, ${image_thumb_path});
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


# Prints out the html-formatted list of files for the page content.
#   printFileListHTML()
sub printFileListHTML {
  # my(@time_info,@month_list);
  # my(${year},${month},${minute},${day},${hour},${file_size},${is_dir});
  my ${file_name};
  my @file_info;
  my ${file_size};
  # list and thumbnail display modes
  if (isMode('list|thumb')) {
    # TODO: Rename file_name to just "file" because it has full path.
    foreach ${file_name} (@dir_list) {
      ${file_size} = '';
      @file_info = stat $ROOT.${file_name};
      # TODO: Delete / recache without loosing info
      if (isMode('list')) {
        # @time_info = localtime ${file_info[9]};
        # EXTRACT FILE INFO FROM ARRAY AND PAD
        # ${year} = ${time_info[5]} + 1900;
        # ${month} = (qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec)) [(${time_info[4]})];
        # ${minute} = (${time_info[1]} < 10) ? "0".${time_info[1]} : ${time_info[1]};
        # ${day} = (${time_info[3]} < 10) ? "0".${time_info[3]} : ${time_info[3]};
        # ${hour} = (${time_info[2]} < 10) ? "0".${time_info[2]} : ${time_info[2]};
        if ( ! isFileType(${file_name},'folder')) {
          ${file_size} = getFormattedFileSize(${file_info[7]});
        }
        print "
        <tr>
          <td class='col-picture'>";
            # GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
            print getIcon(${file_name});
            print "</td>
          <td class='col-description'>";
            # Date isn't really used, but maybe in future?
            # my ${date} = "${day}-${month}-${year} ${hour}:${minute}";
            print getLinkTag(${file_name}, getParsedFileName(${file_name}), '', 'simple');
            if ($file_descriptions{${file_name}}) {
              print "<span class='file-description'>$file_descriptions{${file_name}}</span>";
            }
          print "</td>
          <td class='col-size'>${file_size}&nbsp;&nbsp;</td>
        </tr>";
      } elsif (isMode('thumb')) {
        # GET THE APPROPRIATE ICON FOR THE FILE, FOLDER, IMAGE, ETC.
        # TODO: Use list just like slideshow.
        print '<table class="picture-icon-container" cellpadding="0" cellspacing="1"><tr><td valign="middle" align="center">';
        print getIcon(${file_name});
        print '</td></tr><tr><td valign="top" class="picture-icon-file-name" align="center">'.getParsedFileName(${file_name}).'</td></tr></table>';
      }
    }
    if (isMode('thumb')) {
      print '<div>&nbsp;</div>';
    }

  } elsif (isMode('single')) {
    # Make sure large thumbs exist for single image mode.
    ${file_name} = $STATE{'pic_cur_file'};
    if (${file_name}) {
      my ${previous_thumb} = "$STATE{'web_dir'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_previous_file'}$IMAGE_GLOBAL{'thumb_ext'}";
      my ${next_thumb} = "$STATE{'web_dir'}$IMAGE_GLOBAL{'prefix_large'}$STATE{'pic_next_file'}$IMAGE_GLOBAL{'thumb_ext'}";
      my ${img_status} = getImageTag($STATE{'pic_previous_file'}, $IMAGE_GLOBAL{'prefix_large'});
      ${img_status} = getImageTag($STATE{'pic_next_file'}, $IMAGE_GLOBAL{'prefix_large'});

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

      <a class='picture-link previous'
         title='Previous image'
         href='".getHREF($STATE{'web_dir'}.$STATE{'pic_previous_file'})."'
         data-old-href='".OLDgetHREF('pic', $STATE{'pic_previous_file'})."'
         >
        <img src='${previous_thumb}'
             data-src='$STATE{'web_dir'}$STATE{'pic_previous_file'}'
             alt=''
             id='picture-prev'>
      </a>
      <a class='picture-link large-picture-wrapper'
         href='".getHREF('', 'slide')."'
         data-old-href='".OLDgetHREF('display_mode', 'slide')."'
         title='Slideshow...'>"
        .getImageTag(${file_name}, '')."
      </a>
      <a class='picture-link next'
         title='Next image'
         href='".getHREF($STATE{'web_dir'}.$STATE{'pic_next_file'})."'
         data-old-href='".OLDgetHREF('pic', $STATE{'pic_next_file'})."'
         >
        <img src='${next_thumb}'
             data-src='$STATE{'web_dir'}$STATE{'pic_next_file'}'
             alt=''
             id='picture-next'>
      </a>
      ";
    }
  } elsif (isMode('slide')) {
    # SLIDESHOW IMAGE MODE
    # TODO: Use this for list|thumb|slide ########################################################################
    print '<ul id="files">';
    # Make sure large thumbs exist
    ${file_name} = $STATE{'pic_cur_file'};
    if (${file_name}) {
      foreach ${file_name} (@dir_list) {
        ${file_size} = '';
        @file_info = stat $ROOT.${file_name};
        # ALL THIS ISDIR SHOULD GO IN THE CACHE FILE!  ALSO NEED TO BE ABLE TO DELETE / RECACHE WITHOUT LOOSING INFO
        # Not used anymore... ${is_dir} = S_ISDIR(${file_info[2]});

        # @time_info = localtime ${file_info[9]};
        # EXTRACT FILE INFO FROM ARRAY AND PAD
        # ${year} = ${time_info[5]} + 1900;
        # ${month} = (qw(Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec)) [(${time_info[4]})];
        # ${minute} = (${time_info[1]} < 10) ? "0".${time_info[1]} : ${time_info[1]};
        # ${day} = (${time_info[3]} < 10) ? "0".${time_info[3]} : ${time_info[3]};
        # ${hour} = (${time_info[2]} < 10) ? "0".${time_info[2]} : ${time_info[2]};
        if ( ! isFileType(${file_name}, 'folder')) {
          ${file_size} = getFormattedFileSize(${file_info[7]});
        }

        my $is_selected = ($STATE{'pic_cur_file'} eq $file_name) ? '1' : '0';
        my $file_type = $file_types{${file_name}};
        my $parsed_file_name = getParsedFileName(${file_name});

        # TODO: data-width and data-height
        print "
        <li>
          <a href='$STATE{'web_dir'}${file_name}'
             class='filename'
             data-selected='${is_selected}'
             data-file-type='${file_type}'
             data-size='${file_size}'
             >${parsed_file_name}</a>
          <div>$file_descriptions{$file_name}</div>
        </li>
        ";
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
    my $cur_idx = $image_hash{ $STATE{'pic_cur_file'} };
    if ($STATE{'pic_cur_file'} && $cur_idx ne '') {
      $STATE{'pic_cur_idx'} = $cur_idx;
    } else {
      # ERROR: Requested picture was not found.
      $STATE{'error_msg'} = 'Picture "'.$STATE{'pic_cur_file'}.'" was not found.';
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
  } elsif ($STATE{'pic_cur_file'}) {
    # ERROR: Tried to access a picture in a folder that has no pictures at all.
    $STATE{'error_msg'} = 'Picture "'.$STATE{'pic_cur_file'}.'" was not found.';
  }

  # Would be ideal if we didn't un-encode then re-encode the url_encoded.  In many cases, $ENV{REQUEST_URI} has what we need!
  # Problem is that there are several ways to get the URL (pic_path param or directly from path if no mod_rewrite)
  $STATE{'web_dir_encoded'} = $STATE{'web_dir'};
  $STATE{'web_dir_encoded'} =~ s/ /%20/g;
  $STATE{'page_description'} = stripHTML(getSitemapDataItem('pageDescription'));
}

# GET READY TO PARTY!
calculateImageListState();

if (${COMMANDLINE}) {
  # print "display_mode : $STATE{'display_mode'}\n";
  commandLineMakeThumbs();
  print "[done]\n";
  exit 0;
}

printHtmlHead();
printHtmlContent();


# RENDER HTML HEAD #############################################################

# Prints out the http header for the HTML page.  If the app is in an error state
# then 404 will be sent and user redirected to home page and jcdsee will exit.
# On the test server, html page will be rendered for debugging.
#   printHtmlHead()
sub printHtmlHead {
  if ($STATE{'error_msg'}) {
    print header(-status => 404, -charset=>'utf-8');
    if (! $STATE{'test_mode'}) {
      # Redirect to home page.
      print '<!DOCTYPE html>
        <html class="jcd"><head>
        <meta charset="utf-8">
        <title>Error: '.$STATE{'error_msg'}.'</title>
        <meta http-equiv="refresh" content="0; url=/" />
        </head></html>';
      exit;
    }
  } else {
    print "Content-Type: text/html\n\n";
  }
}

# Prints out content of the page.
#   printHtmlContent()
sub printHtmlContent {
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
      <link rel="canonical" href="'.$STATE{'canonical_url'}.'" />
      <link href="'.${ASSETS}.'/jcdsee.css" rel="stylesheet" type="text/css">
      <!--[if lt IE 8]><script src="http://ie7-js.googlecode.com/svn/version/2.1(beta4)/IE8.js"></script><![endif]-->
  ';

  if ($STATE{'test_mode'}) {
    # Make it pink if in test mode.
    print "<style type='text/css'> body {outline: 1px solid red;background-color: pink;} </style>";
  }

  # Social media tags.  TODO: Make image configurable.
  print '
      <meta property="og:title" content="'.$STATE{'title'}.'" />
      <meta property="og:url" content="'.$STATE{'canonical_url'}.'">
      <meta property="og:description" content="'.$STATE{'page_description'}.'">';
      if ($STATE{'pic_cur_file'}) {
        print '
        <meta property="og:image" content="'.$STATE{'protocol'}.$STATE{'server_name'}.urlEscapeSpaces($STATE{'web_full_path_clean'}).'" />
        <meta property="og:image:type" content="image/jpeg" />';
      }
      print '
      <meta property="fb:admins" content="3994" />
    </head>
    <body id="mode-'.$STATE{'display_mode'}.'" data-adminurl="'.${ASSETS}.'/admin/index.cgi?display_url&cur_url='.$STATE{'web_dir'}.'">

      <div id="nav">
        <ul id="depth-path">'
          .getDepthPath().'
        </ul>
        <div id="mode-buttons">'
          .getNavButton('display_mode', 'list',   'List display mode')
          .getNavButton('display_mode', 'thumb',  'Thumbnail image mode')
          .getNavButton('display_mode', 'single', 'Single image display mode')
          .getNavButton('display_mode', 'slide',  'Slideshow display mode')
          .'
        </div>
      </div>

      <div id="content">
        <div>';
          # Show warning if trying to access slideshow without JS.
          if (isMode('slide')) {
            print '
            <noscript>
              <h1>JavaScript is disabled</h1>
              <h2>Sorry, the slideshow function requires JavaScript. Please choose a different display mode from the top-right corner or wait and this page will be redirected in 10 seconds.</h2>
              <meta http-equiv="refresh" content="10; url='.getHREF('', 'single').'" data-old-href="'.OLDgetHREF('display_mode', 'single').'">
            </noscript>
            ';
          }

          # TODO: Use slideshow list instead of this table.
          if (isMode('list')) {
            print '
            <table id="file_list" cellpadding="4" cellspacing="0" border="0">';
          }
          printFileListHTML();
          # Finish table for list mode.
          if (isMode('list')) {
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
      if ($STATE{'error_msg'} && $STATE{'test_mode'}) {
        my ${debug_info_window} = '';
        ${debug_info_window} .=  "FILE TYPES: \n";
        foreach my $k (sort keys %file_types) {
          ${debug_info_window} .= "  $k = $file_types{$k}\n";
        }
        ${debug_info_window} .=  "\nIMAGES: \n";
        foreach my $k (sort keys %image_hash) {
          ${debug_info_window} .= "  $k = $image_hash{$k}\n";
        }
        ${debug_info_window} .=  "\nSTATE: \n";
        foreach my $k (sort keys %STATE) {
          ${debug_info_window} .= "  $k = $STATE{$k}\n";
        }
        print "
          <div style='margin-top:11px;border:2px solid red;background-color:#f99;font-size:9px;font-family:verdana,sans-serif;color:#a00;'>
            <b style='font-size:10px;color:black;'>ERROR:</b><br>
            <pre>${debug_info_window}</pre>
          </div>";
      }

      $TIMER{'total_e'} = gettimeofday();
      $TIMER{'total'} = sprintf("%.3f", ($TIMER{'total_e'} - $TIMER{'total_s'}));

      print '
      <div id="footer">
        <a id="copyleft" rel="license" href="https://creativecommons.org/licenses/by-nc-sa/4.0/" target="_blank">
          <img alt="Creative Commons License" src="'.$ICON{'copyleft'}.'">
        </a>
        <div id="usage">
          <a href="https://github.com/jonathancross/pics.jonathancross.com" title="See the latest source code behind this website.">JCDSee '.${VERSION}.'</a><br>
          Script executed in: '.$TIMER{'total'}.' seconds.';
          if ($STATE{'country_code'}) {
            print " Your Location: $STATE{'country_code'}";
          }
          print '<br>'
          .getSitemapDataItem('pageDate')
          .getSitemapDataItem('pageSize')
          .'
        </div>
      </div>

      <script src="'.${ASSETS}.'/jcdsee.js"></script>
    </body>
  </html>
  ';
} # End printContent
