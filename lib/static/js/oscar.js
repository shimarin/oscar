angular.module("Oscar", ["ngResource","ui.bootstrap"])
.controller("IndexController", ["$scope", "$resource", function($scope, $resource) {
    var info = $resource("./_info");
    $scope.info = info.get();
}])
.run(["$rootScope","$modal", function($scope,$modal) {
    $scope.about = function() {
        $modal.open({
            templateUrl:"about.html"
        });
    }
}]);
