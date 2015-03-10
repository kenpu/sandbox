var model = {
    t : "container",
    c : [
        {
            t: "container",
            c: [
            {
                t: "html",
                html: "<p>This is react</p> <p>Thanks.</p>",
            }, {
                t: "html",
                html: "We can <b>change</b> the world...",
            }, 
            ],
        },
        {
            t: "html",
            html: "<i>Cool stuff</i>",
        },
        {
            t: "html",
            html: "<ul><li>1</li><li>2</li></ul>",
        }
    ]
};

var updateModel = function() {
    var container = {
        t: "container",
        c: [
        { t: "html",
            html: "<table border=1><tr><td>okay</td></tr></table>",
        }],
    };

    model.c[0].c.push(container);
    return model;
};
