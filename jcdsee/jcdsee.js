/**
 * JCDSee file navigator and slideshow.
 * @author Jonathan Cross.
 * @url http://pics.jonathancross.com
 * @see https://github.com/jonathancross/pics.jonathancross.com
 */
"use strict";

var jcd = {};

/**
 * Image SlideShow Class.
 * @param {Object} config Configuration options:
 *     imageManager: {jcd.ImageManager} An image manager instance.
 *     contentContainer: {Element} Parent of the #files element.
 *     opt_playButtonId: {string=} Element Id.
 *     opt_pauseButtonId: {string=} Element Id.
 *     opt_restartButtonId: {string=} Element Id.
 * @constructor
 */
jcd.SlideShow = function(config) {
  /**
   * @type {!jcd.ImageManager}
   */
  this.imageManager = config.imageManager;

  /**
   * @enum {Element}
   * @private
   */
  this.contentContainer_ = config.contentContainer;

  /**
   * Counter text UI element.
   * @private {!Element}
   */
  this.counterEl_;

  /**
   * @private {Object} reference to DOM nodes used in slideshow.
   */
  this.nodes_;

  /**
   * @private {number} Millisecond delay between image advances.
   */
  this.selectedInterval_;

  /**
   * @private {number} Numeric id of current slideshow timer.
   */
  this.timer_;

  /**
   * @enum {Element} Mapping of UI buttons where key == id and value == element.
   * @private
   */
  this.buttons_ = {};

  /**
   * Configuration of slideshow buttons and actions.
   * TODO: Can these be passed in or derived from DOM?
   * @private {!Array.<!Object.<string, (string|function())>>}
   */
  this.buttonConfig_ = [
    {
      'label': 'play',
      'id': config.opt_playButtonId || this.controlIds_.PLAY_BUTTON,
      'method': function(e) {
        this.play(/* isStale */ true);
      }
    },
    {
      'label': 'pause',
      'id': config.opt_pauseButtonId || this.controlIds_.PAUSE_BUTTON,
      'method': this.pause
    },
    {
      'label': 'restart',
      'id': config.opt_restartButtonId || this.controlIds_.RESTART_BUTTON,
      'method': this.restart
    }
  ];
};


/**
 * Interval speed presets (in milliseconds) used by the SlideShow class.
 * @enum {number}
 * @private
 */
jcd.SlideShow.prototype.intervals_ = {
  FAST : 2000,
  NORMAL : 7000,
  SLOW : 11000
};


/**
 * HTML element IDs used by SlideShow controls such as buttons, counter, etc.
 * @enum {string}
 * @private
 */
jcd.SlideShow.prototype.controlIds_ = {
  NAV: 'nav', // TODO: Delete this and use jcd.Page.navElement_.NAV instead.
  CONTROLS: 'slideshow-controls',
  COUNTER: 'counter',
  BUTTON_CONTAINER: 'slideshow-buttons',
  PLAY_BUTTON: 'slideshow-play',
  PAUSE_BUTTON: 'slideshow-pause',
  RESTART_BUTTON: 'slideshow-restart',
  INTERVAL_SELECTOR: 'slideshow-speed' // TODO: Change to slideshow-interval
};


/**
 * Initializes the slideshow and starts playing.
 */
jcd.SlideShow.prototype.init = function() {
  this.selectedInterval_ = this.intervals_.NORMAL;

  // Create the DOM layout for image and text.
  this.createContentDom_();
  this.initSlideShowControls_();
  console.log(' + SlideShow:');
  console.dir(this);
  this.updateCounter();
  this.play(/* isStale */ false);
};


/**
 * Creates slideshow UI controls.
 * @private
 */
jcd.SlideShow.prototype.initSlideShowControls_ = function() {
  var slideShowControls = document.createElement('div');
  slideShowControls.id = this.controlIds_.CONTROLS;
  slideShowControls.appendChild(this.getSlideShowButtons_());
  slideShowControls.appendChild(this.getIntervalSelectControl_());
  slideShowControls.appendChild(this.getCounterEl_());
  document.getElementById(this.controlIds_.NAV).appendChild(slideShowControls);
};


/**
 * Creates, then returns the image counter UI element.
 * @returns {!Element}
 * @private
 */
jcd.SlideShow.prototype.getCounterEl_ = function() {
  this.counterEl_ = document.createElement('div');
  this.counterEl_.id = this.controlIds_.COUNTER;
  return this.counterEl_;
};


/**
 * Generates a list of slideshow buttons.
 * @returns {!HTMLUListElement} <ul> element containing the slideshow buttons.
 * @private
 */
jcd.SlideShow.prototype.getSlideShowButtons_ = function() {
  var slideShowButtons = document.createElement('ul');
  slideShowButtons.id = this.controlIds_.BUTTON_CONTAINER;

  for (var i = 0, buttonConfig; buttonConfig = this.buttonConfig_[i]; i++) {
    var li = document.createElement('li');
    var button = this.getSlideShowButton_(buttonConfig);
    this.buttons_[buttonConfig.id] = button;
    li.appendChild(button);
    slideShowButtons.appendChild(li);
  }
  return slideShowButtons;
};


/**
 * Generates a button control.
 * @param {!Object} buttonConfig Settings for the button.
 * @returns {!HTMLButtonElement} A slideshow button control.
 * @private
 */
jcd.SlideShow.prototype.getSlideShowButton_ = function(buttonConfig) {
  var button = document.createElement('button');
  button.id = buttonConfig.id;
  button.textContent = buttonConfig.label;
  // var methodType = id.substring(id.lastIndexOf('-') + 1);
  jcd.utils.addEvent(button, 'click', buttonConfig.method.bind(this));
  return button;
};


/**
 * Generates the <select> element for slideshow speed control.
 * @returns {!Element} A new <select> element.
 * @private
 */
jcd.SlideShow.prototype.getIntervalSelectControl_ = function() {
  var select = document.createElement('select');
  select.id = this.controlIds_.INTERVAL_SELECTOR;
  // TODO: consider using strings instead of numbers for this.selectedInterval_.
  for (var intervalName in this.intervals_) {
    var option = document.createElement('option');
    var interval = this.intervals_[intervalName];
    option.textContent = intervalName + ' - ' + (interval / 1000) + 's';
    option.value = intervalName;
    if (interval == this.selectedInterval_) {
      option.selected = true;
    }
    select.appendChild(option);
  }
  // Add change event.
  jcd.utils.addEvent(select, 'change', this.handleSelectedInterval_.bind(this));
  return select;
};


/**
 * Generates the DOM for the main content area of the page.
 * @private
 */
jcd.SlideShow.prototype.createContentDom_ = function() {
  // Disable next and previous buttons in V1:
  //   <button title="Previous image" class="previous picture-link"></button>
  //   <button title="Next image" class="next picture-link"></button>';
  //       Landscape image name: Asia.Bahasa-Indonesia.png
  // this.fileListContainer_.parentNode.innerHTML = '<h3><strong>NAME</strong>Description here ???</h3><div class="picture-link large-picture-wrapper"><img src="images/23_Sign_Wizard.jpg" alt=""></div>';
  // Starting DOM code:
  this.nodes_ = {
    domFragment: document.createDocumentFragment(),
    fileHead: document.createElement('h3'),
    fileDescriptionEl: document.createElement('span'),
    fileNameEl: document.createElement('strong'),
    imageContainerEl: document.createElement('div'),
    imageEl: document.createElement('img')
  };
  this.nodes_.imageContainerEl.className = 'picture-link large-picture-wrapper';
  this.nodes_.fileNameEl.textContent = 'Loading...';
  this.nodes_.fileHead.appendChild(this.nodes_.fileNameEl);
  this.nodes_.fileHead.appendChild(this.nodes_.fileDescriptionEl);
  this.nodes_.domFragment.appendChild(this.nodes_.fileHead);
  this.nodes_.domFragment.appendChild(this.nodes_.imageContainerEl);
  this.nodes_.imageContainerEl.appendChild(this.nodes_.imageEl);
  this.contentContainer_.appendChild(this.nodes_.domFragment);
};


/**
 * Handles change event for interval selector.
 * @param {Event} e Change event.
 * @private
 */
jcd.SlideShow.prototype.handleSelectedInterval_ = function(e) {
  var intervalName = e.target.options[e.target.selectedIndex].value;
  console.log('intervalName changed to: '+ intervalName);
  this.changeInterval_(intervalName);
};


/**
 * Activates a button and updates state.
 * @param {string} id Button id.
 */
jcd.SlideShow.prototype.activateButtonId = function(id) {
  if (this.activeButton) {
    // TODO: Prevent class clobbering.
    this.activeButton.parentNode.className = '';
  }
  this.activeButton = this.buttons_[id];
  this.activeButton.parentNode.className = 'active';
  this.activeButton.focus();
};


/**
 * Constructs an image object and requests the image data.
 * This should be called when you actually want to load AND DISPLAY the image.
 * @param {!jcd.File} file Image file.
 */
jcd.SlideShow.prototype.loadImage = function(file) {
  console.log('Image requested: ' + file.href);
  if (this.imageManager.imageCache[file.href]) {
    this.updateUI_();
    // cache hit
    return;
  }
  file.image = new Image();
  // TODO: Use jcd.utils.addEvent(file.image, 'load', this.updateUI_.bind(this));
  file.image.onload = this.updateUI_.bind(this); // TODO: Only update the UI if image loaded AND time should be advanced.
  file.loaded = false; // move this to jcd.File constructor?
  file.image.src = file.href;
  this.imageManager.imageCache[file.href] = file.image;
};


/**
 * Changes the interval (speed) of the slideshow.
 * @param {string} intervalName Name from this.intervals_ enum.
 * @private
 */
jcd.SlideShow.prototype.changeInterval_ = function(intervalName) {
  if (this.intervals_[intervalName]) {
    this.selectedInterval_ = this.intervals_[intervalName];
    console.log('Interval changed to: ' + this.selectedInterval_);
    this.play(/* isStale */ true);
  }
};


/**
 * Updates UI to show current image, file name and description.
 * @private
 */
jcd.SlideShow.prototype.updateUI_ = function() {
  var selectedImage = this.imageManager.getSelectedImage();
  this.nodes_.fileNameEl.textContent = selectedImage.fileName;
  // Only display the file description element if there is description text.
  if (selectedImage.description) {
    /* TODO: Strip html, then use .textContent */
    this.nodes_.fileDescriptionEl.innerHTML = selectedImage.description;
    this.nodes_.fileDescriptionEl.style.display = 'inline';
  } else {
    this.nodes_.fileDescriptionEl.innerHTML = '';
    this.nodes_.fileDescriptionEl.style.display = 'none';
  }
  this.nodes_.imageEl.src = selectedImage.href;
};


/**
 * Starts the slideshow, then calls autoPlay().
 * @param {boolean} isStale Triggers immediate advance to next image if true.
 *   Generally this is triggered by user clicking a button or changing playback
 *   speed.
 */
jcd.SlideShow.prototype.play = function(isStale) {
  console.log('Starting slideshow with image: ' + this.imageManager.getSelectedImage().href + '\n - isStale: ' + isStale + '\n - Interval: ' + this.selectedInterval_);
  if (isStale) {
    // Immediately advance to next image because current one is stale.
    this.next();
  } else {
    // Load current selected image.
    this.loadImage(this.imageManager.getSelectedImage());
  }
  window.clearTimeout(this.timer_);
  this.timer_ = 0;
  // TODO: delete from config, or make this smarter to use that setting for id.
  this.activateButtonId(this.controlIds_.PLAY_BUTTON);
  this.autoPlay();
};


/**
 * Begins the transition from current image to next.  Will repeat indefinitely.
 */
jcd.SlideShow.prototype.autoPlay = function() {
  this.timer_ = window.setInterval(
    this.next.bind(this),
    this.selectedInterval_
  );
};


/**
 * Retrieves and displays next image in list.
 */
jcd.SlideShow.prototype.next = function() {
  this.loadImage(this.imageManager.getNextImage());
  this.updateCounter(); // TODO: Do this inside loadImage?
};


/**
 * Retrieves and displays previous image in list.
 */
jcd.SlideShow.prototype.previous = function() {
  this.loadImage(this.imageManager.getPreviousImage());
  this.updateCounter(); // TODO: Do this inside loadImage?
};


/**
 * Pauses the slideshow on current image.
 */
jcd.SlideShow.prototype.pause = function() {
  console.log(' + PAUSE: clearing this.timer: ' + this.timer_);
  window.clearInterval(this.timer_);
  this.timer_ = 0;
  this.activateButtonId(this.controlIds_.PAUSE_BUTTON);
};


/**
 * Restarts the slideshow from beginning.
 */
jcd.SlideShow.prototype.restart = function() {
  this.activateButtonId(this.controlIds_.RESTART_BUTTON);
  // Restarts the counter, next and prev
  this.imageManager.goToIndex(0);
  this.updateCounter();
  console.log(' + RESTART. Setting image to first: ' + this.imageManager.getSelectedImage().href);
  window.clearInterval(this.timer_);
  this.loadImage(this.imageManager.getSelectedImage());
  // Start playing from beginning.
  this.play(/* isStale */ false);
};


/**
 * Updates the visual counter to match current state.
 * TODO: This is called a bunch of times from random places.  Better to just
 *       update the UI when state changes.
 */
jcd.SlideShow.prototype.updateCounter = function() {
  var curentNum = this.imageManager.getSelectedIndex() + 1;
  var counterText = 'Image ' + curentNum +' of ' + this.imageManager.length + '.';
  this.counterEl_.textContent = counterText;
};



/**
 * Collection of jcd.File objects and meta data.
 * @param {!Element} container HTML Element.
 * @constructor
 */
jcd.FileList = function(container) {
  this.imageManager = new jcd.ImageManager();
  this.container = container;
  this.files = this.getFiles(this.container);
  this.length = this.files.length;
  this.imageManager.loadImages(this.files);
  // this.url = '/pics/2002/2002-07-20_Chicago/'; /* Get this out of the url? */
  console.log(' + files:');
  console.dir(this.files);
};


/**
 * Container class for images and associated meta data.
 * @constructor
 */
jcd.ImageManager = function() {
  this.files = [];
  this.indexes = {};
  this.length = 0;
  /**
   * Index of selected image.
   * @private {number}
   */
  this.selectedIndex_ = 0;
  this.previousIndex = 0;
  this.nextIndex = 0;

  /**
   * Image found at this.selectedIndex_.
   * @private {!Image}
   */
  this.selectedImage_;

  /**
   * List of images that have been requested already.
   * @enum {!Image}
   */
  this.imageCache = {};
};


/**
 * Retrieves this.selectedImage_.
 * @returns {!Image}
 */
jcd.ImageManager.prototype.getSelectedImage = function() {
  return this.selectedImage_;
};


/**
 * Retrieves this.selectedImage_.
 * @returns {!Image}
 */
jcd.ImageManager.prototype.getSelectedIndex = function() {
  return this.selectedIndex_;
};


/**
 * Retrieves next image index.
 * @returns {number} Index number of next image in list or first if looping.
 * @private
 */
jcd.ImageManager.prototype.getNextImageIndex_ = function() {
  return (this.isEnd()) ? 0 : this.selectedIndex_ + 1;
};


/**
 * Advances selectedIndex forward and returns Image at that index.
 * @returns {!Image}
 */
jcd.ImageManager.prototype.getNextImage = function() {
  this.goToIndex(this.getNextImageIndex_());
  return this.selectedImage_;
};


/**
 * Retrieves previous image index.
 * @returns {number} Index number of previous image in list or last if looping.
 * @private
 */
jcd.ImageManager.prototype.getPreviousImageIndex_ = function() {
  return (this.isBegin()) ? this.lastIndex : this.selectedIndex_ - 1;
};


/**
 * Moves selectedIndex back to previous position.
 * @returns {!Image}
 */
jcd.ImageManager.prototype.getPreviousImage = function() {
  this.goToIndex(this.getPreviousImageIndex_());
  this.updateCounter();
  return this.selectedImage_;
};


/**
 * Sets the selectedIndex to an arbitrary number and updates state.
 * @param {number} index Index number to set as current image.
 */
jcd.ImageManager.prototype.goToIndex = function(index) {
  this.selectedIndex_ = index;
  this.selectedImage_ = this.files[this.selectedIndex_];
  this.updateNextPrev(); // TODO: Move to SlideShow?
};


/**
 * Tells us if we are at the end of the list of images.
 * @returns {boolean} selectedIndex is last item in this.files.
 */
jcd.ImageManager.prototype.isEnd = function() {
  return (this.selectedIndex_ === this.lastIndex);
};


/**
 * Tells us if we are at the beginning of the list of images.
 * @returns {boolean} selectedIndex is 0.
 */
jcd.ImageManager.prototype.isBegin = function() {
  return (this.selectedIndex_ === 0);
};


/**
 * Updates previous and next states.
 */
jcd.ImageManager.prototype.updateNextPrev = function() {
  this.nextIndex = this.getNextImageIndex_();
  this.previousIndex = this.getPreviousImageIndex_();
};


/**
 * Loads file list information from DOM.
 * @returns {!Array.<jcd.File>} Array of File objects.
 */
jcd.FileList.prototype.getFiles = function() {
  var files = [];
  var fileInfoItems = this.container.getElementsByTagName('li');
  for (var i = 0, a, li, fileData; li = fileInfoItems[i]; i++) {
    a = li.getElementsByClassName('filename')[0];
    fileData = {
      description: li.getElementsByTagName('div')[0].innerHTML,
      fileName: a.textContent,
      height: a.getAttribute('data-height'),
      href: a.href,
      isSelectedImage: a.getAttribute('data-selected'),
      size: a.getAttribute('data-size'),
      type: a.getAttribute('data-file-type'),
      width: a.getAttribute('data-width')
    };

    files[i] = new jcd.File(fileData);
  }
  return files;
};


/**
 * Processes array of jcd.File objects into lists of images.
 * @param {!Array.<jcd.File>} files List of File objects.
 */
jcd.ImageManager.prototype.loadImages = function(files) {
  for (var i = 0, imageCounter = 0, file; file = files[i]; i++) {
    if (file.type == jcd.File.prototype.fileTypes_.PIC) {
      // should files and indexes be private?
      this.files.push(file);
      this.indexes[file.fileName] = imageCounter;
      if (file.isSelectedImage) {
        this.selectedIndex_ = imageCounter;
        this.selectedImage_ = file;
      }
      imageCounter++;
    }
  }
  this.length = imageCounter;
  this.lastIndex = imageCounter - 1;
};


/**
 * Generic File class.  See recognized FileTypes_.
 * @param {!Object} fileData File information supplied from DOM.
 * @constructor
 */
jcd.File = function(fileData) {
  this.description = fileData.description;
  this.fileName = fileData.fileName;
  this.href = fileData.href;
  this.size = fileData.size || '0b';
  this.type = this.validateFileType(fileData.type);

  // Begin properties for specific file types
  // Pictures
  if (this.type == this.fileTypes_.PIC) {
    // Convert to boolean
    this.isSelectedImage = (fileData.isSelectedImage == '1');
    this.height = Number(fileData.height);
    this.width = Number(fileData.width);
  }

  // All files that are not folders
  if (this.type != this.fileTypes_.FOLDER) {
    this.extension = fileData.href.replace(/^.*\./, '');
  }
};


/**
 * Recognized file types.
 * @enum {string}
 * @private
 */
jcd.File.prototype.fileTypes_ = {
  DOC : 'doc',
  FOLDER : 'folder',
  MUSIC : 'music',
  PIC : 'pic', /* refactor to IMG ? */
  UNKNOWN : 'unknown'
};


/**
 * UNUSED: Intended to be called when an image is successfully loaded.
 * TODO: perhaps this should call a callback (eg SlideShow.updateUI_?)
 * @private
 */
jcd.File.prototype.imageLoaded_ = function () {
  console.log('  - loaded image: '+this.src);
  this.loaded = true;
};


/**
 * Returns the validated type of a file.
 * @param {string} type Type specified in source.
 * @returns {string} A recognized file type or 'unknown'.
 */
jcd.File.prototype.validateFileType = function(type) {
  return this.fileTypes_[type.toUpperCase()] || this.fileTypes_.UNKNOWN;
};


/**
 * Add x-browser shim for bind().
 */
if (!Function.prototype.bind) {
  /** @param {!Object} oThis The 'this' object we want to bind to. */
  Function.prototype.bind = function (oThis) {
    if (typeof this !== 'function') {
      // Try to duplicate ECMAScript 5 internal IsCallable function.
      throw new TypeError('Function.prototype.bind - what is trying to be ' +
                          'bound is not callable');
    }
    var aArgs = Array.prototype.slice.call(arguments, 1),
        fToBind = this,
        fNOP = function() {},
        fBound = function() {
          return fToBind.apply(this instanceof fNOP && oThis
               ? this
               : oThis,
             aArgs.concat(Array.prototype.slice.call(arguments)));
    };
    fNOP.prototype = this.prototype;
    fBound.prototype = new fNOP();
    return fBound;
  };
}



/**
 * Namespace for utility functions.
 */
jcd.utils = {};


/**
 * Adds x-browser event listener to an element.
 * @param {!Element} el Element we want to attach event to.
 * @param {string} event Browser event name.
 * @param {!Function()} func Callback.
 */
jcd.utils.addEvent = function(el, event, func) {
  if (el.addEventListener) {
    el.addEventListener(event, func, false);
  } else if (el.attachEvent) {
    el.attachEvent('on' + event, func);
  } else {
    el['on' + event] = func;
  }
};


/**
 * Main class representing a page.
 * @constructor
 */
jcd.Page = function() {
  /**
   * @private {!Element} file list.
   */
  this.fileListContainer_;

  /**
   * @private {!Image} Image element for next button.
   */
  this.nextImgEl_;

  /**
   * @private {!Image} Image element for previous button.
   */
  this.prevImgEl_;

  /**
   * @private {string} Display mode as defined in HTML id of body element. Will
   *                   be one of jcd.Page.prototype.displayModes_
   */
  this.displayMode_;

  /**
   * @private {!Object} Main content area DOM elements.
   */
  this.content_;

  this.init_();
};


/**
 * HTML element IDs used on every page.
 * @enum {string}
 * @private
 */
jcd.Page.prototype.elementIds_ = {
  NAV: 'nav',
  CONTENT: 'content'
};


/**
 * Recognized display modes.
 * @enum {string}
 * @private
 */
jcd.Page.prototype.displayModes_ = {
  LIST: 'list',
  THUMB: 'thumb',
  SINGLE: 'single',
  SLIDE: 'slide'
};


/**
 * Returns a valid display mode.
 * @returns {string} A valid display mode from jcd.Page.prototype.displayModes_,
 *                   or the default of 'list'.
 */
jcd.Page.prototype.getDisplayMode = function() {
  var modeStr = document.body.id.replace(/^mode-/, ''); // Strip off prefix.
  return this.displayModes_[modeStr.toUpperCase()] || this.displayModes_.LIST;
};


/**
 * Caches the next & previous images so they load fast if clicked in list mode.
 * TODO: Fold this into slideshow code later.
 */
jcd.Page.prototype.cacheNextPrev = function() {
  // TODO: Make these IDs lowercase:
  this.nextImgEl_ = document.getElementById('NEXT');
  this.prevImgEl_ = document.getElementById('PREVIOUS');
  var nextImgSrc = this.nextImgEl_.getAttribute('data-src'),
      prevImgSrc = this.prevImgEl_.getAttribute('data-src');
  if (nextImgSrc && prevImgSrc) {
    this.nextImgEl_.src = nextImgSrc;
    this.prevImgEl_.src = prevImgSrc;
  } else {
    // Fail quietly.
    console.log('ERROR: Could not load "src" data attributes for next / previous.');
  }
};


/**
 * Generates a transparent login link.
 * @returns {Element} adminButton
 * @private
 */
jcd.Page.prototype.getAdminControl_ = function() {
  var adminButton = document.createElement('div');
  adminButton.id = 'admin-button';
  adminButton.title = 'Login';
  jcd.utils.addEvent(adminButton, 'click', function() {
    // Opens link to Admin console.
    window.open(document.body.getAttribute('data-adminurl'));
  });
  return adminButton;
};


/**
 * Creates initial DOM structure of page.
 * @private
 */
jcd.Page.prototype.createDom_ = function() {
  // Hide the list of files.
  this.fileListContainer_.className += ' hide';
  this.fileListContainer_.parentNode.className += ' active';
};


/**
 * Initializes the page, sets up slideshow from file list and encapsulates vars.
 * @private
 */
jcd.Page.prototype.init_ = function() {
  this.footerEl_ = document.getElementById('footer');
  this.fileListContainer_ = document.getElementById('files');
  this.navElement_ = document.getElementById(this.elementIds_.NAV);
  this.displayMode_ = this.getDisplayMode();
  // console.log('DEBUG: Page display mode: ' + this.displayMode_);

  if ((this.displayMode_ == this.displayModes_.SLIDE) && this.fileListContainer_) {
    var fileList = new jcd.FileList(this.fileListContainer_);
    var slideShow = new jcd.SlideShow({
      'imageManager': fileList.imageManager,
      'contentContainer': this.fileListContainer_.parentNode // TODO: Better way to handle contentContainer?  Don't like how it is being passed around.
    });
    slideShow.init();
    this.createDom_();
  } else if (this.displayMode_ == this.displayModes_.SINGLE) {
    jcd.utils.addEvent(window, 'load', this.cacheNextPrev.bind(this));
  } else {
    // DEBUG: Could not find #files = will not start slideshow.
  }

  // Insert Admin link
  this.footerEl_.appendChild(this.getAdminControl_());
};


new jcd.Page();
