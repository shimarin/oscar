angular.module("Oscar", ["ngResource","ngSanitize","ui.bootstrap"])
.controller("IndexController", ["$scope", "$resource", function($scope, $resource) {
    var info = $resource("./_info");
    $scope.info = info.get({}, function(result) {
        angular.forEach(result.shares, function(share) {
            share.info = $resource("./" + share.name + "/_info").get();
        }, function() {
            $scope.info = {error:true}
        });
    });
    $scope.alert_class = function(loadavg) {
        var classes = ["alert"];
        if (alert > 3.0) {
            classes.push("alert-danger");
        } else if (alert > 1.0) {
            classes.push("alert-warning");
        } else {
            classes.push("alert-success");
        }
        return classes;
    }
}])
.controller("ShareController", ["$scope", "$resource","$location","$timeout", function($scope, $resource,$location,$timeout) {
    var info = $resource("./_info");
    var dir = $resource("./_dir");
    var search = $resource("./_search");
    var filetypes = {
        ".ai":"ai", ".avi":"avi",
        ".bmp":"bmp",
        ".cab":"cab", ".css":"css",
        ".dll":"dll", ".doc":"doc", ".docx":"docx", ".dot":"dot", ".dwg":"dwg", ".dxf":"dxf",
        ".emf":"emf", ".eml":"eml", ".eps":"eps", ".exe":"exe",
        ".fla":"fla", ".fon":"fon",
        ".gif":"gif", ".gz":"gz",
        ".hqx":"hqx", ".htm":"html", ".html":"html",
        ".ico":"ico",
        ".jar":"jar", ".jpg":"jpg", ".js":"js", ".jtd":"jtd",
        ".log":"log", ".lzh":"lzh",
        ".m4a":"m4a", ".m4v":"m4v", ".mdb":"mdb", ".mid":"mid", ".mov":"mov", ".mp3":"mp3", ".mp4":"mp4", ".mpg":"mpg",
        ".ogg":"ogg",
        ".pdf":"pdf", ".php":"php", ".png":"png", ".ppt":"ppt", ".pptx":"pptx", ".ps":"ps", ".psd":"psd",
        ".rtf":"rtf",
        ".sit":"sit", ".swf":"swf",
        ".tar":"tar", ".tgz":"tgz", ".tiff":"tiff", ".ttc":"ttc", ".ttf":"ttf", ".txt":"txt",
        ".vbs":"vbs",
        ".wav":"wav", ".wma":"wma", ".wmf":"wmf", ".wmv":"wmv", ".wri":"wri",
        ".xls":"xls", ".xlsx":"xlsx", ".xml":"xml",
        ".zip":"zip"
    };
    $scope.path = $location.path();
    $scope.path_elements = [];
    $scope.q = null;
    $scope.limit = 20;
    $scope.search = null;

    $scope.timer = null;

    $scope.load = function(path) {
        $scope.path_elements = $scope.split_path(path);
        $scope.info = info.get({path:$scope.path}, function() {}, function() { $scope.info = {error:true} });
        $scope.dir = dir.query({path:$scope.path});
    }

    $scope.load($scope.path);

    function exec_search(path, q, limit) {
        $scope.search = search.get({path:path,q:q,limit:limit}, function() {
        }, function() {
            s = { error:true }
        });
    }

    $scope.$watchCollection("[path, q, limit]", function(newValues,oldValues) {
        var path = newValues[0];
        var oldpath = oldValues[0]
        var q = newValues[1];
        var oldq = oldValues[1];
        var limit = newValues[2];
        if ($scope.timer) {
            $timeout.cancel($scope.timer);
            $scope.timer = null;
        }
        if (path !== oldpath) { // pathが変わった場合はinfo, dirもリロード
            $scope.load(path);
        }
        if (q) {
            if (q === oldq) {// qが一緒でpathやlimitが変わっただけなら即時に検索
                exec_search(path, q, limit);
            } else {
                $scope.timer = $timeout(function() {
                    exec_search(path,q, limit);
                }, $scope.search && $scope.search.$resolved === false? 500 : 100); // 既に検索が走っていれば500ms, フリーなら100ms
            }
        }
        else $scope.search = null;
    });

    $scope.filetype = function(name) {
        var re = /(?:\.([^.]+))?$/;
        var suffix = re.exec(name)[0];
        if (!suffix || !filetypes.hasOwnProperty(suffix)) return null;
        return filetypes[suffix];
    }

    $scope.$on('$locationChangeSuccess', function() {
        $scope.path = $location.path();
    });

    $scope.move_to = function(path) {
        if (path == "..") {
            path_spl = $scope.split_path(path);
            if (path_spl.length > 0) {
                path_spl.length = path_spl.length - 1;
            }
            path = path_spl.join("/");
        }
        $location.path(path);
    }

    $scope.open_file = function(path, name) {
        window.open($scope.join_path('.',$scope.join_path(path, name)));
    }

}])

.run(["$rootScope","$location", "$modal", function($scope,$location,$modal) {
    $scope.Math = window.Math;
    $scope.about = function() {
        $modal.open({
            templateUrl:"about.html"
        });
    }
    $scope.iehelp = function() {
        $modal.open({
            templateUrl:"iehelp.html"
        });
    }
    $scope.eden_link = function(share, path, name) {
        var link = "file://///" + $location.host();
        if (share) {
            link = $scope.join_path(link, share);
            if (path) {
                link = $scope.join_path(link, path);
                if (name) {
                    link = $scope.join_path(link, name);
                }
            }
        }
        return link;
    }
    $scope.join_path = function(path1, path2) {
        path1 = path1.replace(/\/+$/, "");
        path2 = path2.replace(/^\/+/, "");
        return path1 + "/" + path2;
    }
    $scope.split_path = function(path) {
        path = path.replace(/\/+$/, "");
        path = path.replace(/^\/+/, "");
        if (path == "") return [];
        return path.split("/");
    }
}]);
