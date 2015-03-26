var React = require('react');

var Node = React.createClass({
    render: function() {
        var text = this.props.text;
        return <li>{text}</li>;
    }
});

module.exports = Node;
