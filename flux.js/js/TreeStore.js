var AppDispatcher = require('./AppDispatcher');
var EventEmitter = require('events').EventEmitter;
var C = require('./Constants');

var store = {
    children: [
        "hello",
        "world",
    ]
};

module.exports = {
    getState: function() {
        return store;
    },

    addItem: function(text) {
        store.children.push(text);
    },
}
