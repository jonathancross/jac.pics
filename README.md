### JCDSee: a web-based photo viewing / cataloging system written in Perl.
* Production server: http://pics.jonathancross.com
* Dev server: http://test-pics.jonathancross.com

#### What it does:
JCDSee creates an HTML directory listing of any folders it finds so that they can be browsed as a website.  Folders can contain any type of document, but it handles photos especially well by creating multiple sizes, navigation helpers and a slideshow mode for sequential viewing.

#### Features:
* Recognizes 5 general file types: image, folder, music, text and "unknown".
  "unknown" file types can include video, or anything else, but will not
  have an icon unless you provide one manually.
* Will generate & cache thumbnail icons of any jpeg, gif or png files it finds.
* Four image display modes: `list`, `thumb`, `single` and `slide`.
* Properly handles slow connections with pre-caching.
* Allows owner to add description of each file / folder.
* Supports dating / numbering of files and folders.
* Will maintain display settings across folders.
* Progressively enhanced: can be used without JavaScript.
* Private: No login, cookies, etc. required.
* Accessible: Can be used with screen readers, keyboard navigation, etc.

#### Commandline debug parameters (YMMV):
You can use this script from the shell to generate thumbnails, create the `.jcdsee` database, debug problems, etc:

    ./jcdsee.cgi debug <directory> <display_mode> <pic_cur_idx>
All arguments in `<>` are optional.

#### URLs
JCDSee supports clean URLs via `mod_rewrite` (see [.htaccess](.htaccess#L27)).
If you link to a folder, that folder will be loaded in `list` mode by default.
* `http://pics.jonathancross.com/pics/1976/`

You can also specify one of four display modes (`list|thumb|single|slide`) as the root folder to change the way images and icons are displayed.
* <code>http:<span></span>//pics.jonathancross.com/**list**/pics/1976/</code> - List mode (just like default above).
* <code>http:<span></span>//pics.jonathancross.com/**thumb**/pics/1976/</code> - Thumbnail mode (less words, bigger pictures).
* <code>http:<span></span>//pics.jonathancross.com/**single**/pics/1976/cat.jpg</code> - Single image display.
* <code>http:<span></span>//pics.jonathancross.com/**slide**/pics/1976/cat.jpg</code> - Begin slideshow starting with "cat.jpg".


##### URL parameters (DEPRECATED):
URL Parameters have been deprecated as part of the "[Better URLs](https://github.com/jonathancross/pics.jonathancross.com/milestones/Better%20URLs)" upgrade.  Ignore this section if using `mod_rewrite`.  If you are using dirty URLs, these are your two options:
* `display_mode=[list|thumb|single|slide]` - defaults to `list` mode.
* `pic_path=/path/to/picture.jpg` - link to a single folder or picture.

#### Database structure
JCDSee generates a very basic flat-file database in each folder named `.jcdsee`.  This file is a pipe-delineated file with this format:

    filename.jpg|Optional HTML description of the file.  

Fancy file name support:
* <code>**2015-08-13**_This-is-the-day.jpg</code> - Date prefix will be understood by the software and displayed differently to visitors.
* <code>**99**_Almost_number_100.png</code> - Simple number prefixes (used to set order, etc) will be hidden from website visitors.
* <code>El Ni**ñ**o.jpg</code> - Spaces and UTF8 characters in file names are okay.

#### Warnings:
* Do not use user-supplied images, files, etc. JCDSee is intended to be used for content you created and are sure is safe.
* The software requires all files to be in a folder called "pics".
* The system tries to prevent unauthorized access to files / folders, but needs more testing.
* Does not use SQL, cookies, sessions, etc.
* On pics.jonathancross.com I use an admin script to automate many tasks (editing database, building the sitemap, etc). This is not currently available on GitHub.
