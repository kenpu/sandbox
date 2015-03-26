var i = 0;
var _ = function() {
    i += 1;
    return i;
};

module.exports = {
    A: _(),
    B: _(),
    C: _(),
    D: _(),
};
