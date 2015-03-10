function Element(x) {
    var y;
    switch(x.t) {
        case "html":
            y = <div className="htm"
                dangerouslySetInnerHTML={{__html: x.html}} />;
            break;
        case "container":
            y = <Container children={x.c} />;
            break;
        default:
            y = <div className="error">Unknown: {x.t}</div>;
    }

    return y;
}

var Container = React.createClass({
    render: function() {
        var elements = this.props.children.map(function(c) {
            return Element(c);
        });

        var h1 = (this.props.name) ? <h1>{this.props.name}</h1> : null;
        return <div className="container">
            {h1}
            {elements}
        </div>
    }
});

var Root = React.createClass({
    getInitialState: function() {
        return {
            model: model,
        }
    },
    componentDidMount: function() {
        var self = this;
        setTimeout(function() {
            self.setState({model: updateModel()});
        }, 1000);
    },
    render: function() {
        return Element(this.state.model);

    },
});
React.render(
        <Root />,
        $("div:first")[0]);
