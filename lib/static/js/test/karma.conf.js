module.exports = function(config) {
    config.set({
        basePath: '..',
        frameworks: ['jasmine'],
        files: [
            "https://code.jquery.com/jquery-latest.min.js",
            'https://code.angularjs.org/1.2.16/angular.js',
            'https://code.angularjs.org/1.2.16/angular-mocks.js',
            'https://code.angularjs.org/1.2.16/angular-sanitize.js',
            "https://ajax.googleapis.com/ajax/libs/angularjs/1.2.16/angular-resource.js",
            "https://cdnjs.cloudflare.com/ajax/libs/angular-ui-bootstrap/0.10.0/ui-bootstrap-tpls.js",
            'oscar.js',
            'test/*.spec.ts'
        ],
        exclude: [
            '**/*.d.ts'
        ],
        preprocessors: {
            '**/*.ts': ['typescript']
        },
        typescriptPreprocessor: {
            // options passed to the typescript compiler
            options: {
                sourceMap: false, // (optional) Generates corresponding .map file.
                target: 'ES5', // (optional) Specify ECMAScript target version: 'ES3' (default), or 'ES5'
                module: 'amd', // (optional) Specify module code generation: 'commonjs' or 'amd'
                noImplicitAny: true, // (optional) Warn on expressions and declarations with an implied 'any' type.
                //noResolve: true, // (optional) Skip resolution and preprocessing.
                removeComments: true // (optional) Do not emit comments to output.
            },
            // transforming the filenames
            transformPath: function(path) {
                return path.replace(/\.ts$/, '.js');
            }
        },
        autoWatch: true
    });
};

