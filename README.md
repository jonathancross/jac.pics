###JCDSee: a web-based photo viewing / cataloging system written in Perl.
* Production server: http://pics.jonathancross.com
* Test server: http://test-pics.jonathancross.com

####What it does:
JCDSee creates an html directory listing of any folders it finds so that they can be browsed as a website.  It is focused around handeling images but can support any type of document.

####Features:
* Recognizes 5 general file types: image, folder, music, text and "unknown".
  "unknown" file types can include video, or anything else, but will not
  have an icon unless you provide one manually.
* Will generate & cache thumbnail icons of any jpeg, gif or png files it finds.
* Four image display modes: "list", "thumbnail", "single" and "slideshow".
* Properly handles slow connections with pre-caching.
* Allows owner to add description of each file / folder.
* Supports dating / numbering of files and folders.
* Will maintain display settings across folders.
* Progressivly enhanced: can be used without JavaScript.
* Private: No login, cookies, etc required.
* Accessible: Can be used with screen readers, keyboard navigation, etc.

####Commandline debug parameters (YMMV):
You can use this script from the shell to generate thumbnails, create the `.jcdsee` database, debug problems, etc:

    ./jcdsee.cgi debug <directory> <display_mode> <pic_cur_idx>
All args in `<>` are optional.

####URL parameters:
Note: All parameters are optional.  If no url is provided, the current location of the script is used with the defaults below.

    ./jcdsee.cgi?pic=[full path to picture]&display_mode=[LIST|THUMBS|SINGLE|SLIDESHOW]&cur_url=[full path to folder]
Defaults:

    display_mode=LIST
    cur_url=<current folder>


####Example URLs:
Assuming JCDSee is in the web root, this would be the URL structure on zzz.com:

    http://zzz.com/
    http://zzz.com/jcdsee.cgi?cur_url=/pics/
    http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg
    http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg&display_mode=SLIDESHOW
    http://zzz.com/jcdsee.cgi?pic=/pics/my_pic.jpg&display_mode=THUMBS

If you use `mod_rewrite`, you can have "clean" URLs like so:
* `http://zzz.com/pics/2/`  (results in: `http://zzz.com/jcdsee.cgi?cur_url=/pics/2/`)

See [.htaccess](https://github.com/jonathancross/pics.jonathancross.com/blob/version2-responsive/.htaccess#L29) file for example.

####Warnings:
* Do not use user-supplied images, files, etc. JCDSee is intended to be used for content you created and are sure is safe.
* The system tries to prevent unauthorized access to files / folders, but needs more testing.
* Does not use SQL, cookies, sessions, etc.
* On pics.jonathancross.com I use an admin script to automate many tasks (editing database, building the sitemap, etc). This is not currently available on GitHub.


