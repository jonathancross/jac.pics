'use strict';
/**
 * Tabset toggler used on homepage.
 * NOTE: This is included using SSI.
 */
(function() {

/**
 * Tab toggler class.
 * @constructor
 */
function Toggler() {
  // Exit if old browser.
  if (!document.body.classList) {
    this.handleOldBrowser();
    return;
  }
  /** @private {!Array.<!Element>} */
  this.tabEls_ = [].slice.call(document.getElementsByClassName(this.TAB_CLASS));
  /** @private {!Array.<string>} */
  this.tabIds_ = this.tabEls_.map(function(el, i, arr){return el.id;})
  /** @private {string} */
  this.firstTabId_ = this.tabIds_[0];
  /** @private {!Object.<string, !Tab>} */
  this.tabObjs_ = {};
  /** @private {string} */
  this.selectedTabId_;
  this.init_();
};

/** @private @const {string} */
Toggler.prototype.TAB_CLASS = 'jcd-tab';


/**
 * Handles older browsers by forcing simpllified display.
 */
Toggler.prototype.handleOldBrowser = function() {
  // Force to look like JS is disabled.
  document.documentElement.className = 'jcd';
};


/**
 * Initializaes all tabs and sets default visibility.
 */
Toggler.prototype.init_ = function() {
  for (var tabId, n = 0; tabId = this.tabIds_[n]; n++) {
    var tab = new Tab(tabId, this);
    this.tabObjs_[tabId] = tab;
    // Register the selected tab id from the url hash.
    if (tab.isInUrlHash()) {
      this.selectedTabId_ = tabId;
    } else {
      tab.hide();
    }
  }

  // Default to first tab is none selected in url.
  if (!this.selectedTabId_) {
    this.selectedTabId_ = this.firstTabId_;
  }

  // Toggle the apropriate tab.
  var selectedTab = this.tabObjs_[this.selectedTabId_];
  selectedTab.show();
};


/**
 * Toggles visibility of a tab.
 * @param {string} tabIdToToggle ID of the tab to show.
 */
Toggler.prototype.toggleTab = function(tabIdToToggle) {
  if (tabIdToToggle == this.selectedTabId_) {
    // Nothing to do.
    return;
  }

  var currentlySelectedTab = this.tabObjs_[this.selectedTabId_];
  // Look for the new tab to toggle.
  for (var tabId, n = 0; tabId = this.tabIds_[n]; n++) {
    if (tabIdToToggle == tabId) {
      currentlySelectedTab.hide();
      this.selectedTabId_ = tabIdToToggle;
      var toggledTab = this.tabObjs_[tabIdToToggle];
      toggledTab.show();
      return;
    }
  }
};


/**
 * Class definition for a single Tab.
 * @param {string} tabId unique id of tab.
 * @param {!Toggler} toggler Toggler.
 * @constructor
 */
function Tab(tabId, toggler) {
  this.tabId = tabId;
  this.toggler = toggler;
  this.content = document.getElementById(this.tabId);
  this.label = document.getElementById(this.tabId + this.LABEL_SUFFIX);
  // TODO: rewrite using bind so we don't have to use global toggler.
  this.label.onclick = function(evt) {
    // Bad use of toggler instance from outside context.
    toggler.toggleTab(tabId);
    evt.preventDefault();
  };
};

/** @private @const {string} */
Tab.prototype.LABEL_SUFFIX = '-label';

/** @private @const {string} */
Tab.prototype.URL_PREFIX = '#tab=';

/** @private @const {string} */
Tab.prototype.CLASS_ACTIVE = 'active';


/** @returns {boolean} true if this tab is selected in URL hash. */
Tab.prototype.isInUrlHash = function() {
  return (document.location.hash == this.URL_PREFIX + this.tabId);
};

/**
 * Sets this tab to selected in URL hash.
 * @private
 */
Tab.prototype.setUrlHashToThisTab_ = function() {
  document.location.hash = this.URL_PREFIX + this.tabId;
};

/** Shows this tab in UI. */
Tab.prototype.show = function() {
  this.label.classList.add(this.CLASS_ACTIVE);
  this.content.classList.add('show');
  this.content.classList.remove('hide');
  this.setUrlHashToThisTab_();
};

/** Hides this tab in UI. */
Tab.prototype.hide = function() {
  this.label.classList.remove(this.CLASS_ACTIVE);
  this.content.classList.remove('show');
  this.content.classList.add('hide');
};

var toggler = new Toggler();

})(); // End Self-executing anonymous function.