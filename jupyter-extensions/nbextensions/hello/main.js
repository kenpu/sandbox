define([
    'base/js/namespace',
    'base/js/events',
    'jquery',
], function(Jupyter, events, $) {
    function load() {
        console.log("Hello world 1:36am");
        Jupyter.toolbar.add_buttons_group([
            Jupyter.keyboard_manager.actions.register({
                'help': 'Hello world help',
                'icon': 'fa-eye',
                'handler': callback,
            }, 'say-hell-world', 'hello_world'),
        ]);
    }

    function callback(Jupyter) {
        console.log("callback...");
        Jupyter.notebook.clear_all_output();
        $('.prompt').css('color', 'red');
    }
    return {
        load_ipython_extension: load,
    };
})
