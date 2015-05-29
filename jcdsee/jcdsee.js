/*
  Javascript used for settings and navigation in JCDSee.
  Jonathan Cross :: 2004-2008
*/
var win = null;
function refresh(name,val) {
  var controls = document.control_form;
  var setting = controls[name];
  if (name == "zoom_mode"){ //Reverse the current zoom mode if clicked
                            //zoom_mode and window_mode are all backwards!
                            //should submit the value we WANT, not the current one, then reverse it!
    setting.value = (setting.value == "ZOOMED_IN")? "ZOOMED_OUT" : "ZOOMED_IN";
  }else if (name == "img_cur_idx"){ //Auto switch to SINGLE display_mode when you click on a thumbnail
    controls["display_mode"].value = "SINGLE";
    setting.value = val;
  }else if (name == "window_mode"){ //toggle full screen window mode
    if (setting.value == "WIN_NORMAL"){ // you are in initial state, window will be opened
      setting.value = "WIN_FULL_SCREEN";
      goFullScreen();
      controls.target = "win";
    }else{ //you are in full screen mode, window will be closed
      setting.value = "WIN_NORMAL";
      controls.target = "opener";
    }
  }else if (name == "directory"){ //Submit to another URL
    controls.target = "_self";
    controls["img_cur_idx"].value = "0";
    if (controls["display_mode"].value == "SINGLE") {
      //When changing directories, can't stay in SINGLE mode because many folders don't contain images
      controls["display_mode"].value = "LIST";
    }
    controls.action = val;
  }else{
    setting.value = val;
  }
  if (name == "window_mode" && val == "WIN_FULL_SCREEN") {
    controls.submit();
    window.close();
  }else if (name == "window_mode") {
    controls.submit();
    controls.target = "_self";
    controls["window_mode"].value = "WIN_NORMAL";
  }else{
    controls.submit();
  }
}
function goFullScreen(url) {
  props = "width=" + (screen.width-10) + ",height=" + (screen.height-50) + ",top=0,left=0,scrollbars=1";
        if (url) {
          win_url=url;
        }else{
          win_url=window.location.href;
        }
  win=window.open(win_url,"win",props);
  if (win.opener == null) { win.opener = window; } 
  win.opener.name = "opener";
  win.focus();
}
/* Add favorites icon */
function adFav() {
  var u = document.location.href;var t=document.title;
  if (document.all) window.external.AddFavorite(u,t);
  else if (window.sidebar) window.sidebar.addPanel(t,u,'');
  else alert('Sorry, your browser dosn\'t support this feature.\nPlease add a link manually.');
}
function cacheImages(previous,next) {
  if (document.control_form.display_mode.value == "SINGLE" && document.images["PREVIOUS"] && document.images["NEXT"]) {
    var prev = new Image();
    var nxt = new Image();
    prev.src = previous;
    document.images["PREVIOUS"].src = prev.src;
    nxt.src = next;
    document.images["NEXT"].src = nxt.src;
  }
}
/********************* SLIDESHOW CODE ***********************/
var isSlideshow=0;
var isInit=1;
var pic,count,description,startLink,stopLink,start,end;
var LIMIT=2;   //images to precache
var INTERVAL_INIT=4000; //speed when doc loads
var INTERVAL_ACCELERATOR=4000; // speed up response for use interaction by 2 seconds
var intervalf = 3000;
var intervalm = 7000;
var intervals = 11000;
var interval = intervalm;
var timerId = -1;
var preCacheArray=new Array();

function init() {
  //var mac = (navigator.userAgent.toLowerCase().indexOf('mac')!=-1);
  if (document.getElementById) {
    pic=document.getElementById('big_pic');
    description=document.getElementById('desc');
    count=document.getElementById('count');
    count.innerHTML='<span style="color:#acf">'+(cur_pic+1)+'</span> of '+image_array.length;
    startLink=document.getElementById('startLink');
    stopLink=document.getElementById('stopLink');
    return (pic)?1:0;
  }else{
    alert('Sorry, your browser is not capable of showing the slideshow -- time to upgrade.');
    document.location.href = url;
  }
}
function nextImage(){
  if (isSlideshow) {
    description.innerHTML='';
    if (document.all){
      pic.style.filter='blendTrans(duration=1)';
      pic.filters.blendTrans.Apply();
    }
    cur_pic=getNextIndex(cur_pic);
    preCache(cur_pic,1);
    count.innerHTML='<span style="color:#acf">'+(cur_pic+1)+'</span> of '+image_array.length;
    var desc='<strong>'+image_array[cur_pic]+'</strong>';
    if(descriptions_array[cur_pic]) desc += ' - '+ descriptions_array[cur_pic];
    pic.setAttribute('src',url+image_array[cur_pic]);
    if (document.all) pic.filters.blendTrans.Play();
    description.innerHTML=desc;
    preCache(cur_pic+1,1);
  }
}
function play(i){
  if (isSlideshow) {
    var thisInterval=(i)?i:interval;
    timerId = window.setTimeout('nextImage();timerId=-1',thisInterval);
  }
}
function loaded() {
  if (isSlideshow){
    play(interval);
  }
}
function getNextIndex(idx) {
  if (idx < (image_array.length-1)){
    return (idx+1);
  }else{
    return 0;
  }
}
function changeSpeed(sidx){
  switch (sidx){
    case 0: interval = intervalm; break;
    case 1: interval = intervals; break;
    default: interval = intervalf;
  }
  if (timerId != -1){
    window.clearTimeout(timerId);
    timerId = window.setTimeout('play(0);timerId=-1',0);
  }
}
function stopSlideshow(){
  stopLink.blur();
  if (pic) {
    startLink.className='slideButton';
    stopLink.className='slideButtonStop';
  }
  isSlideshow=0;
  window.clearInterval(timerId);
  if (timerId != -1) {
    window.clearTimeout(timerId);
    timerId = -1;
  }
  preCache(cur_pic,5);
}
function preCache(idx,limit){
  lim=(limit)?limit:LIMIT;
  for (var i=idx;i<image_array.length && i<(idx+lim);i++) {
    preCacheArray[i]=new Image();
    preCacheArray[i].src=''+url+image_array[i];
  }
}
function startSlideshow(){
  var thisInterval;
  if (isInit) {
    preCache(cur_pic,4);
    thisInterval = INTERVAL_INIT;
    isInit=0;
  }else{
    thisInterval = interval - INTERVAL_ACCELERATOR; // 2 secs faster if they clicked the button.  Improved "response".
  }
  isSlideshow=1;
  if (init()){
    startLink.blur(); //get rid of ugly outline
    startLink.className='slideButtonStart';
    stopLink.className='slideButton';
    play(thisInterval);
  }
}
