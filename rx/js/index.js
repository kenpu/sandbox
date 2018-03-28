var Rx = require('rx').Rx;
var f = function(x) {
    console.log(">>>>", x)
    for(var i=0; i < 5000000000; i++) {
    }
    console.log("<<<<", x);
}
var u = Rx.Observable.interval(100);
var v = Rx.Observable.interval(400);
// u.buffer(v).subscribe(f);
u.subscribe(f)


