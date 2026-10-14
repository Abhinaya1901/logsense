sap.ui.define([
	"sap/ui/core/mvc/Controller",
	"sap/ui/core/routing/History",
	"../model/formatter"
], function (Controller, History, formatter) {
	"use strict";

	return Controller.extend("logsense.controller.ProductDetail", {
		formatter: formatter,

		onInit: function () {
			this.getOwnerComponent().getRouter().getRoute("detail")
				.attachPatternMatched(this._onRouteMatched, this);
		},

		_onRouteMatched: function (oEvent) {
			var sProductId = oEvent.getParameter("arguments").productId;
			this.getView().bindElement({
				path: "/Products(" + encodeURIComponent(sProductId) + ")",
				parameters: { expand: "Category,Supplier" }
			});
		},

		onNavBack: function () {
			if (History.getInstance().getPreviousHash() !== undefined) {
				window.history.go(-1);
			} else {
				this.getOwnerComponent().getRouter().navTo("products", {}, true);
			}
		}
	});
});
