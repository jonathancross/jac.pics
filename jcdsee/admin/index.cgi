#!/bin/bash
VERSION=1.9.7
ADMIN_SCRIPT_NAME="index.cgi"
CACHE_FILE=".jcdsee" # Should be renamed to DATABASE and used with edit.database
BACKUP_PREFIX="$(date +'%Y-%m-%d')"
ROOT="../pics"
BACKUP_DIR="BACKUP"
ADMIN_SCRIPT="${ADMIN_SCRIPT_NAME}"
PICS="pics"
MASTER="${ROOT}/${PICS}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}.data.txt"
JCD_LIVE="${ROOT}/jcdsee.cgi"
JCD_TEST_FILE="${ROOT}/.test/jcdsee.cgi"
JCD_PUBLIC="${ROOT}/jcdsee_latest.txt"
SITEMAP_BIN="${ROOT}/jcdsee/admin/sitemap.cgi"
SITEMAP_FILE="${ROOT}/sitemap.xml"
percent='%%'
I=0
CUR_URL=""
isCUR_URL=0
# File separator hack
IFS=$'\n'

prefix() {
  local line
  while read line; do printf "$1%s\n" "$line";done
}


# Unencode the url spaces and break up params into list
PARAMS=$(echo "${QUERY_STRING}" | sed 's/%20/ /g' | tr '&' '\n'); # Fix syntax highlight '
for PARAM in ${PARAMS[@]};do
  if [ "${PARAM%=*}" == "cur_url" ];then
    CUR_URL="${PARAM#*=}"
    # Fix the url by removing trailing slashes and spaces and adding trailing slash if necessary.
    CUR_URL="$(printf ${CUR_URL} | sed 's/[/]*$//')/"
    # URL TESTS
    # 1. Its not empty.
    # 2. It begins with a '/' and doesn't contain '/..'
    # 3. It is under the pics root dir.
    if [ "${CUR_URL}" -a "$(printf ${CUR_URL} | sed s/.*[/][.][.].*//)" -a "${CUR_URL:0:1}" == "/" -a -d "${MASTER}/${CUR_URL#/${PICS}/}" ];then
      isCUR_URL=1
    else
      isCUR_URL=0
    fi
  else
    COMMANDS[${I}]=${PARAM};
  fi
  let "I++"
done

I=0
printf "Content-type: text/html\r\n\r\n"
printf "
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>JCDSee Admin Console ${VERSION}</title>
  <style type='text/css'>
    BODY {background-color:#ddd;}
    INPUT,PRE,DIV.display_url {font-family:'courier new',courier,mono;font-size:11px;}
    #cur_url {width:50em;}
    A.red_b,A.b {display:block;text-align:center;color:#333;text-decoration:none;font-weight:bold;font-family:arial,sans-serif;border:1px solid #666;background-color:#ccc;width:8em;padding:2px;font-size:15px;border-radius:3px;}
    A.red_b {background-color:#faa;color:red;border-color:#933;}
    A.red_b:hover {border-color:#f00;background-color:#f88;color:#a00;}
    A.b:hover {border-color:#123;background-color:#def;color:#234;}
    #file-list {float:right;border:1px solid #bbb;background-color:#eee;border-radius:3px;padding:0 10px 12px;font-size:10px;color:#888;margin: 0 10${percent};}
    .error {color:red;font-weight:bold;}
    BLOCKQUOTE {color:#999;font-size:11px;margin-bottom:0px;padding-bottom:0px;}
    .head {color:#666;font-size:15px;font-weight:bold;font-family:arial,sans-serif;}
    .date {color:#66a;font-weight:normal;font-size:12px;}
    .display_url {color:#334455;font-size:12px;}
    TD {font-family:Arial,sans-serif;font-size:12px;}
    TD.button {text-align:right;}
    TEXTAREA {background-color:#222;color:white;font-family:'Lucida Console',fixedsys,monaco,courier,mono;font-size:12px;width:100${percent};}
    FORM {margin:0px;padding:0px;}
    table {margin-left:0}
    .links {font-family: arial; clear:both;}
    .links > a:before {content:'|';margin: 0 7px;color:#999;display: inline-block;cursor:text;}
    .links > a.first:before {content:'';display:none;}
  </style>
  <script type='text/javascript'>
  //<![CDATA[
  function shrink() {
    var elem = document.getElementById('file');
    elem.style.fontSize='9px';
    elem.cols='100';
    elem.rows='30';
  }
 function confirmForm(str) {
    if(confirm(str)) {
      return true;
    }else{
      return false;
    }
  }
  function addURL(command,sub) {
    var cur_url=document.myform.cur_url.value;
    if (cur_url != '') {
      if (command) {
        document.location.href='${ADMIN_SCRIPT_NAME}?'+command+'&cur_url='+cur_url;
      }else{
        document.location.href='${ADMIN_SCRIPT_NAME}?cur_url='+cur_url;
      }
    }else {
      if (command) {
        document.location.href='${ADMIN_SCRIPT_NAME}?'+command;
      }else{
        document.location.href='${ADMIN_SCRIPT_NAME}';
      }
    }
    if (sub) {
      document.fileform.submit();
    }else{
      return false
    }
  }
   // ]]>
  </script>
</head>
<body>

<a class='b' href='http://logout:logout@pics.jonathancross.com/jcdsee/logout' style='float:right;'>TODO:LOGOUT</a>
<a class='b' title='test-pics.jonathancross.com' href='http://test-pics.jonathancross.com/pics/' target='_blank' style='float:right;margin-right:200px;'>TEST SERVER</a>
<span class='head'>JCDSee Admin Console v${VERSION}.<br /><code class='date'>$(date)</code>
</span>
<pre>";
printf "<form name='myform' onsubmit='return addURL(\"display_url\",0)'>";
if [ "${isCUR_URL}" == "0" -a "${CUR_URL}" != "" ];then
  echo "<div class='error'>[ERROR: INVALID URL!]</div>
<pre>
DOCUMENT_ROOT: $DOCUMENT_ROOT
ROOT: $ROOT
isCUR_URL: $isCUR_URL
CUR_URL: $CUR_URL
PICS:
"
ls -al ../pics/
echo "
</pre>
"
else
  for COMMAND in ${COMMANDS[@]};do
    if [ "${COMMAND}" == "display_url" ];then
      echo "<div class='display_url'>URL Set to: \"<span style='color:#012;'>${CUR_URL}</span>\"</div>"
    fi
  done
fi
printf "<table><tr><td>URL: <input type='text' size='50' name='cur_url' id='cur_url' value='${CUR_URL}' /></td><td><a class='b' href='javascript:addURL(\"display_url\",0)'>Set URL</a></td></tr></table>"
printf "</form>"
# printf "<blockquote>"
I=0
if [ -d "${MASTER}" ];then
  for COMMAND in ${COMMANDS[@]};do
    if [ ${I} -gt 0 ];then
      printf "\n-------------------------------------------------------\n"
    fi
    if [ "${COMMAND}" == "display_url" ];then
      printf;
    elif [ "${COMMAND}" == "clean.data" ];then
      if (( ${isCUR_URL} ));then
        echo "Using current url..."
        cd "${ROOT}${CUR_URL}"
      else
        echo "<div class='error'>[ERROR: Database cleanup requires a current URL!]</div>";break;
      fi
      echo "DELETING DATABASES FOR: $(pwd)<br>"
      printf " Confirming backup... "
      if [ -f "${BACKUP_FILE}" ];then
        for FILE in $(find . -name ${CACHE_FILE} -maxdepth 2);do
            printf "  Deleting \"${FILE}\"... "
            if $(rm -f "${FILE}");then
              echo "[SUCCESS]";
            else
              echo "<div class='error'>[ERROR: DELETE FAILED!]</div>";exit 0;
            fi
#echo "  Rebuilding ${FILE}"
#./index.cgi debug > /dev/null
        done
      else
        echo "<div class='error'>[ERROR: BACKUP FILE NOT FOUND!]</div>";exit 0;
      fi
    elif [ "${COMMAND}" == "backup.data" ];then
      cd ${MASTER}
      echo "BACKING UP DATABASES FOR: ${MASTER}<br>"
      for FILE in $(find . -name ${CACHE_FILE});do
        if [ -w "${BACKUP_DIR}" ] ;then
          echo " Backing up \"${FILE}\"... "
          printf "\n#${FILE}\n" >> "${BACKUP_FILE}"
          cat "${FILE}" >> "${BACKUP_FILE}"
          chmod 644 "${BACKUP_FILE}"
         else
          echo "<div class='error'>[ERROR: BACKUP FAILED!]</div>";exit 0;
        fi
      done
    elif [ "${COMMAND}" == "flatfile.sitemap" ];then
      FLATFILE_DB=.jcdsee_global
      cd ${ROOT}
      echo "CREATING FLATFILE DATABASE: ${ROOT}/${FLATFILE_DB}<br>"
      DIRS=$(find "${PICS}" -type d ! -regex '.*/[.].*' | sort)
      # This isn't ideal as we will have a broken DB for a few seconds...
      echo '' > "${FLATFILE_DB}"
      I=0;
      for DIR in ${DIRS[@]};do
        cat "${DIR}/.jcdsee" | prefix "/${DIR}/" >> "${FLATFILE_DB}"
        let I++
      done
      chmod 644 "${FLATFILE_DB}"
      echo "Done. ${I} albums added."
    elif [ "${COMMAND}" == 'add.albums' ];then ##############  2012 : maybe merge with make.thumbs -- will jcdsee commandline make the database?
      # NO FUNCTIONALITY BELOW YET
      FULL_DIR=''
      cd ${MASTER}
      DIRS_SKIPPED=0;
      DIRS_TOTAL=0;
      DIRS_NEW=0;
      IFS=$'\n'; # consider local IFS'
      for DIR in $(find . -type d | sort);do
        DIR="${DIR:2}"
        TMP="${DIR##*/}"
        if [ ! -d ${DIR} ];then echo "<span class='error'> [ERROR] </span> /${PICS}/${DIR} is not a directory!";fi
        if [ "${TMP:0:1}" == "." -o "${DIR:0:1}" == "." ];then
          echo "- Skipping hidden folder: /${PICS}/${DIR}"
          let DIRS_SKIPPED++;
        elif [ -d "${MASTER}/${DIR}" ];then
          if [ "${DIR}" != '' ];then
            FULL_DIR="${MASTER}/${DIR}"
            let DIRS_TOTAL++;
            # 2012: this section below could run jcdsee if there is no .jcdsee database present
            if [ ! -f "${FULL_DIR}/.jcdsee" ];then
              echo "<div class='error'> + Found new Folder: /${PICS}/${DIR}</div>";
              # 2012 : make thumbnails here
              echo "    COMMAND: ./jcdsee.cgi debug \"${PICS}/${DIR}/\""
              let DIRS_NEW++;
            fi;
          else
            FULL_DIR="${MASTER}"
            # 2012 : make thumbnails here
            #printf "Relinking: ROOT"
            echo "    COMMAND: ./jcdsee.cgi debug \"${PICS}/${DIR}/\""
            let DIRS_TOTAL++;
          fi
        else echo "<div class='error'>[ERROR: FOLDER PROBLEM WITH '${MASTER}/${DIR}' (name perhaps)]</div>";exit 0;
        fi
      done
      printf "\nFOLDERS: Skipped: ${DIRS_SKIPPED} &nbsp;|&nbsp; Newly added: ${DIRS_NEW} &nbsp;|&nbsp; Total: ${DIRS_TOTAL}\n"
    elif [ "${COMMAND}" == "clean.misc" ];then
      cd ${MASTER}
      FILES=$(find . -name Picasa.ini -o -name Thumbs.db);
      if [ "${FILES[*]}" ];then
        for FILE in ${FILES[@]};do
          printf "Cleaning out: '${FILE}'"
          if $(rm -f "${FILE}");then
            echo " [SUCCESS]";
          else echo " [FAILED]";
          fi
        done
      else echo "[ Nothing to cleanup ]";
      fi
      printf "+ Fixing all folder permissions... "
      if $(chmod -R 755 "${MASTER}");then echo " [SUCCESS]";
      else echo "<span class='error'> [FAILED]</span>";break;
      fi;
    elif [ "${COMMAND}" == "pub.jcd_test" ];then
      echo "Attempting to publish JCDSee."
      printf "+ Testing...  "
      #2>&1
      if $(perl -c "${JCD_TEST_FILE}");then
        printf "[ PASSED ]\n+ Copying...  "
        if $(cp -f "${JCD_TEST_FILE}" "${JCD_LIVE}" && chmod 711 "${JCD_LIVE}")
        then
          echo "[ SUCCESS ]"
          printf "+ Creating public version... "
          if $(cp -f "${JCD_TEST_FILE}" "${JCD_PUBLIC}" && chmod +r "${JCD_PUBLIC}");
            then echo " [SUCCESS]";
          else
            echo "<span class='error'> [FAILED]</span>";break;
          fi;
        else
          echo "<span class='error'>[ FAILED ]</span>"
        fi
      else
        echo "<span class='error'>[ TEST FAILED ]</span>"
      fi
    elif [ "${COMMAND}" == "reset.jcd_test" ];then
      printf "Resetting with live version of JCDSee.\n  Copying...  "
      if $(cp -f "${JCD_LIVE}" "${JCD_TEST_FILE}")
        then echo "[ SUCCESS ]"
        else echo "<span class='error'>[ FAILED ]</span>"
      fi
    elif [ "${COMMAND%.*}" == "edit" ];then
      if [ "${COMMAND}" == "edit.jcd" ];then
        EDIT_FILE="${JCD_LIVE}"
        BAK="${BACKUP_DIR}/${BACKUP_PREFIX}_jcdsee.txt"
        printf "Backing up file... "
        if cp ${EDIT_FILE} ${BAK} && chmod 644 ${BAK};then echo "[ ${BAK##*/www} ] [ SUCCESS ]";else echo "[ FAILED ]";fi
      elif [ "${COMMAND}" == "edit.jcd_test" ];then
        EDIT_FILE="${JCD_TEST_FILE}"
        BAK="${BACKUP_DIR}/${BACKUP_PREFIX}_jcdsee_test.txt"
        printf "Testing the file...  "
        #2>&1
        if $(perl -c "${JCD_TEST_FILE}");then
          printf "[ PASSED ]\nBacking up file..."
          if cp ${EDIT_FILE} ${BAK} && chmod 644 ${BAK};then echo "[ ${BAK##*/www} ] [ SUCCESS ]";else echo "<span class='error'>[ FAILED ]</span>";fi
        else
          echo "<span class='error'>[ TEST FAILED ]</span>"
        fi
      elif [ "${COMMAND}" == "edit.admin" ];then
        EDIT_FILE="${ADMIN_SCRIPT}"
        BAK="${BACKUP_DIR}/${BACKUP_PREFIX}_${VERSION}_index.txt"
        printf "Backing up file... "
        if cp -f ${EDIT_FILE} ${BAK} && chmod 644 ${BAK};then echo "[ ${BAK##*/www} ] [ SUCCESS ]";else echo "[ FAILED ]";fi
      elif [ "${COMMAND}" == "edit.database" ];then
        if (( ${isCUR_URL} ));then
          echo "Loading Data...\"${ROOT}${CUR_URL}.jcdsee\""
          EDIT_FILE="${ROOT}${CUR_URL}.jcdsee"
        else
          echo "<div class='error'>[ERROR: Database editing requires a current URL!]</div>";break;
        fi
      else
        echo "[ ERROR: Could not recognize the file you want to edit. ]"
        exit 1
      fi
      # Read STDIN to see if there is POST data.  If so, write it to the file.
      read FILE_TEXT
      if [ "${FILE_TEXT}" ];then
        if [ -w ${EDIT_FILE} ];then
          # Not sure what I am doing here...
          # Translate + to spaces?  Then convert from base 64 back to normal text and fix line endings.
          echo "${FILE_TEXT#*=}" | tr '+' ' ' | perl -pe 's/%([0-9a-fA-F][0-9a-fA-F])/pack("c",hex($1))/eg' | perl -pe 's/\r\n/\n/g' > ${EDIT_FILE}.tmp
          mv ${EDIT_FILE}.tmp ${EDIT_FILE}
          printf "File Saved...  "
          chmod 711 ${EDIT_FILE}
          ls -al ${EDIT_FILE}
          echo "[ DONE ]"
        else
          echo "[ ERROR: Could not write to \"${EDIT_FILE}\" ]"
        fi
      fi
      # Edit a file in the browser.
      if [ -r "${EDIT_FILE}" ];then
        echo "<form method='post' name='fileform' onsubmit='return addURL(\"edit.test\",1)'>"
        printf "<table style='width:800px'><tr><td><a class='b' href='javascript:;' onclick='shrink()'>shrink</a></td><td><span style='font-size:13px;font-family:verdana;'>${EDIT_FILE}</span></td><td align='right'><input type='submit' value='Save File \"${EDIT_FILE##*/}\"' /></td></tr></table>"
        echo "<textarea cols='137' rows='37' name='file' id='file' wrap='off'>$(cat ${EDIT_FILE} | sed 's/&/\&amp;/g' | sed 's/</\&lt;/g')</textarea>"
        printf "<input type='submit' value='Save File \"${EDIT_FILE##*/}\"' /></form>";
      else
        echo "[ No file to edit ]"
      fi
    elif [ "${COMMAND}" == "clean.thumbs" ];then
      if [[ ${isCUR_URL} && "${CUR_URL:0:6}" == "/${PICS}/" ]];then
        echo "Using current url..."
        cd "${ROOT}${CUR_URL}"
      else
        echo "<div class='error'>[ERROR: Thumbnail cleanup requires a current URL under /${PICS}/ !]</div>";break;
      fi
      echo "STARTING FIND..."
      IFS=$'\n';
      # To find all possible thumbnail extensions:
      # find . -regex '^.*/[.][SL][.].*[.]jpg$' | egrep -o '[^.]+[.]jpg$' | sort -u
      # 2012-01-05 this was: JPG.jpg, avi.jpg, gif.jpg, jpg.jpg, mpg.jpg, png.jpg, psd.jpg
      # We want this script to only delete the ones JCDSee can recreate: JPG.jpg, gif.jpg, jpg.jpg, png.jpg (TODO: psd.jpg?)
      for FILE in $(find . -regex '.*/[.][SL][.].*[.]\(jpg\|JPG\|gif\|png\)[.]jpg$');do
        printf "Cleaning out: '${FILE}'"
        if $(rm -f "${FILE}");then
          echo " [SUCCESS]";
        else
          echo " [FAILED]";
        fi
      done
    elif [ "${COMMAND}" == "sitemap" ];then
      if [ -x "${SITEMAP_BIN}" ];then
        echo "Rebuilding Sitemap with fresh data..."
        if ${SITEMAP_BIN} 2>&1;then
          echo "New sitemap: $(ls -al ${SITEMAP_FILE}). <a href='/sitemap.xml' target='_new'>[View it]</a> | <a href='http://www.google.com/ping?sitemap=http://pics.jonathancross.com/sitemap.xml' target='_new'>[Send to google]</a>"
        else echo " <div class='error'>[FAILED]</div>";
        fi
      else echo "<div class='error'> [ERROR] Could not execute: ${SITEMAP_BIN}</div>";
      fi
    elif [ "${COMMAND}" == "make.thumbs" ];then
      if [[ ${isCUR_URL} && "${CUR_URL:0:6}" == "/${PICS}/" ]];then
        echo "Using current url..."
        cd "${ROOT}"
      else
        echo "<div class='error'>[ERROR: Thumbnail cleanup requires a current URL under /${PICS}/ !]</div>";break;
      fi
      IFS=$'\n'; # Fix syntax highlighting '
      # Below in our list of dirs, we remove the trailing / to normalize output as first match always has it, others dont
      for D in $(find .${CUR_URL%/} -type d);do
        printf "  Making thumbs for: ${D#.}/"
        export OUTPUT="$(./jcdsee.cgi debug "${D}/")"
        if [[ $? == "0" ]];then
          TOTAL_THUMBS=$(echo "$OUTPUT" | grep -c ' \+ ')
          TOTAL_THUMBS_CREATED=$(echo "$OUTPUT" | grep -c 'CREATED')
          if [[ "$TOTAL_THUMBS_CREATED" == "0" ]];then
            echo " [UP TO DATE]";
          else
            echo " [<strong>${TOTAL_THUMBS_CREATED}</strong> of ${TOTAL_THUMBS} thumbnails updated]";
          fi
        else
          echo " [FAILED $? ] ${OUTPUT}";
        fi
      done
    elif [ "${COMMAND}" == "test" ];then
      if [ -d "${MASTER}" ];then
        echo "Test worked!<br>"
      fi
    elif [ "${COMMAND}" != "" ];then
      echo "<div class='error'>[ERROR: UNRECOGNIZED COMMAND \"${COMMAND}\"]</div>"
    fi
    let "I++"
  done
else
  echo "<div class='error'>[ERROR: NO SOURCE DIR!]</div>";exit 0;
fi
# printf "</blockquote>"
if [ "${COMMAND%%.*}" != "edit" -a "${COMMAND%%.*}" != "display_url" ];then
  echo "[DONE]<br /><hr />"
fi
echo "</pre>";
if (( ${isCUR_URL} ));then
  echo "<pre id='file-list'><h3>${CUR_URL}</h3>$(ls -1 ${ROOT}${CUR_URL})</pre>";
fi
echo "<table border='0' cellpadding='3'>

  <tr><td class='button'><a class='b' href='javascript:addURL(\"flatfile.sitemap\",0)'>flatfile.sitemap</a></td><td>Make new flatfile sitemap (<a href='http://pics.jonathancross.com/.jcdsee_global' target='_blank'>.jcdsee_global</a>) database. STILL UNDER DEV</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"backup.data\",0)'>backup.data</a></td><td>Backup all file description databases.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"clean.misc\",0)'>clean.misc</a></td><td>Clean out random junk files (Thumbs.db, Picasa.ini) and fix permissions.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"edit.jcd\",0)'>edit.jcd</a></td><td>Edit main perl script behind JCDSee.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"edit.jcd_test\",0)'>edit.jcd_test</a></td><td>Edit the testing script for JCDSee.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"pub.jcd_test\",0)'>pub.jcd_test</a></td><td>Publish changes made to testing script.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"edit.admin\",0)'>edit.admin</a></td><td>Edit this Admin script.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"edit.database\",0)'>edit.database</a></td><td>Edit the database for the current folder.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"add.albums\",0)'>add.albums</a></td><td>List all new folders (no real functionality now, but maybe merge with make.thumbs later?).</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"sitemap\",0)'>sitemap</a></td><td>Rebuilds the google sitemap.xml file.</td></tr>
  <tr><td class='button'><a class='b' href='javascript:addURL(\"test\",0)'>Test</a></td><td>Test</td></tr>
  <tr><td colspan='2'><hr /></td></tr>
  <tr><td class='button'><a class='red_b' href='javascript:addURL(\"reset.jcd_test\",0)' onclick='return confirmForm(\"DESTROY ALL CHANGES TO JCDSEE TEST?\n(There is no way to undo!)\")'>reset.jcd_test</a></td><td>Copies the live version over the test script.</td></tr>
  <tr><td class='button'><a class='red_b' href='javascript:addURL(\"make.thumbs\",0)' onclick='return confirmForm(\"Create new thumbnails in all sub folders?\")'>make.thumbs</a></td><td>Recursively create large and small thumbnail images for all albums (recursive).</td></tr>
  <tr><td class='button'><a class='red_b' href='javascript:addURL(\"clean.thumbs\",0)' onclick='return confirmForm(\"DELETE THUMBS IN THIS DIR???\n(There is no way to undo!)\")'>clean.thumbs</a></td><td>Clean out cached thumbnail image files (recursive).  Will only delete thumbnails that jcdsee can regenerate: JPG, gif, jpg, png.</td></tr>
  <tr><td class='button'><a class='red_b' href='javascript:addURL(\"backup.data&amp;clean.data\",0)' onclick='return confirmForm(\"DELETE ALL DATABASES???\n(There is no way to undo!)\")'>clean.data</a></td><td>Backup, then delete ALL file info databases in the cur url.</td></tr>
  <tr><td colspan='2'><hr /></td></tr>
</table>
<div class='links'>
  <a href='https://www.cloudflare.com/a/caching/jonathancross.com' target='_blank' class='first'>CloudFlare settings</a>
  <a href='BACKUP/' target='_blank'>View BACKED UP Files</a>
</div>
<hr />
<span style='font-family:verdana,arial;font-size:10px;'>
USAGE: ${0}?[make.flatfile.sitemap|backup.data|clean.misc|make.thumbs|clean.thumbs|clean.data|edit.jcdsee|edit.admin|edit.database|test]<br />
       [cur_url]=[url]
</span>
</body>
</html>"
