var React = require('react');
var TreeStore = require('./TreeStore');
var Node = require('./TreeNode.react');

var TreeApp = React.createClass({
    getInitialState: function() {
        return TreeStore.getState();
    },

    render: function() {
        var list = this.state.children;
        console.debug("state", this.state);
        var children = [];
        if(list) {
            children = list.map(function(text, i) {
                return <Node text={text} key={i} />;
            });
        }
        return  <div>
                    <h1>Tree App</h1>
                    <ul> {children} </ul>
                    <button onClick={this.addItem}> Add </button>
                </div>;
    },

    addItem: function() {
        TreeStore.addItem("another");
    },
});

module.exports = TreeApp;
