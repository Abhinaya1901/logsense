sap.ui.define([
	"sap/ui/core/mvc/Controller",
	"sap/ui/model/Filter",
	"sap/ui/model/FilterOperator",
	"sap/m/MessageToast",
	"../model/formatter"
], function (Controller, Filter, FilterOperator, MessageToast, formatter) {
	"use strict";

	var LOW_STOCK_THRESHOLD = 10;

	return Controller.extend("logsense.controller.Products", {
		formatter: formatter,

		onInit: function () {
			this._iSimulation = 0;
		},

		onFilterChange: function () {
			var sQuery = this.byId("productSearch").getValue();
			var bLowStock = this.byId("lowStockCheck").getSelected();
			var aFilters = [];

			if (sQuery) {
				aFilters.push(new Filter("ProductName", FilterOperator.Contains, sQuery));
			}
			if (bLowStock) {
				aFilters.push(new Filter("UnitsInStock", FilterOperator.LT, LOW_STOCK_THRESHOLD));
			}

			this.byId("productsTable").getBinding("items").filter(
				aFilters.length ? new Filter({ filters: aFilters, and: true }) : []
			);
		},

		onItemPress: function (oEvent) {
			var iProductId = oEvent.getSource().getBindingContext().getProperty("ProductID");
			this.getOwnerComponent().getRouter().navTo("detail", { productId: iProductId });
		},

		onOpenTroubleshoot: function () {
			this.getOwnerComponent().getRouter().navTo("troubleshoot");
		},

		/**
		 * Fires realistic failing OData calls so the error-capture and AI analysis
		 * can be demonstrated. Each failure is picked up by util/ErrorLog.
		 */
		onSimulateError: function () {
			var oModel = this.getView().getModel();
			var sToast = this.getOwnerComponent().getModel("i18n").getResourceBundle().getText("errorCaptured");
			var fnDone = function () {
				MessageToast.show(sToast);
			};
			var aScenarios = [
				// 400: filtering on a property that does not exist in the entity type
				function () {
					oModel.read("/Products", {
						filters: [new Filter("Price", FilterOperator.GT, 10)],
						error: fnDone
					});
				},
				// 404: entity set that does not exist
				function () {
					oModel.read("/ProductCatalog", { error: fnDone });
				},
				// 404: key that does not exist
				function () {
					oModel.read("/Products(99999)", { error: fnDone });
				}
			];
			aScenarios[this._iSimulation % aScenarios.length]();
			this._iSimulation++;
		}
	});
});
