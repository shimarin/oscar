/// <reference path="jasmine.d.ts" />
/// <reference path="angular.d.ts" />
/// <reference path="angular-mocks.d.ts" />

describe("Oscar", () => {
    var $rootScope : ng.IRootScopeService;
    var $httpBackend : ng.IHttpBackendService;
    var $controller:ng.IControllerService;
    beforeEach(module("Oscar"));
    beforeEach(inject( (_$controller_:ng.IControllerService,_$rootScope_:ng.IRootScopeService,_$httpBackend_:ng.IHttpBackendService) =>{
        $rootScope = _$rootScope_;
        $httpBackend = _$httpBackend_;
        $controller = _$controller_;
    }));

    describe("ShareController", () => {
        var $scope : any;
        beforeEach( ()=> {
            $scope = $rootScope.$new()
            $controller("ShareController", {$scope:$scope});
        });
        it("filetype", ()=> {
            expect($scope.filetype("hoge.zip")).toBe("zip");
        });
        it("move_to", () => {
            $scope.path = "/hoge/foo/bar/";
            $scope.move_to("..");
        });
    });
});
