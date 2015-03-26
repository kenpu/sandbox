var React = require('react');

var TreeApp = require('./TreeApp.react');

console.debug("Treeapp", TreeApp);

React.render(
        <TreeApp />,
        document.getElementById('treeapp'));

