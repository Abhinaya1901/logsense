sap.ui.define([
	"sap/ui/core/mvc/Controller",
	"sap/ui/core/routing/History",
	"sap/ui/model/json/JSONModel",
	"sap/base/strings/formatMessage",
	"sap/m/MessageBox",
	"sap/m/MessageToast",
	"../model/formatter"
], function (Controller, History, JSONModel, formatMessage, MessageBox, MessageToast, formatter) {
	"use strict";

	return Controller.extend("logsense.controller.Troubleshoot", {
		formatter: formatter,
		formatMessage: formatMessage,

		onInit: function () {
			this.getView().setModel(new JSONModel({
				input: "",
				context: "odata",
				busy: false,
				result: null
			}), "view");
		},

		_text: function (sKey, aArgs) {
			return this.getOwnerComponent().getModel("i18n").getResourceBundle().getText(sKey, aArgs);
		},

		onSelectEntry: function (oEvent) {
			var oEntry = oEvent.getParameter("listItem").getBindingContext("log").getObject();
			var oViewModel = this.getView().getModel("view");
			oViewModel.setProperty("/input", this.getOwnerComponent().getErrorLog().toText(oEntry));
			oViewModel.setProperty("/context", "odata");
			oViewModel.setProperty("/result", null);
		},

		onClear: function () {
			var oViewModel = this.getView().getModel("view");
			oViewModel.setProperty("/input", "");
			oViewModel.setProperty("/result", null);
			this.byId("errorList").removeSelections(true);
		},

		onExplain: function () {
			var oViewModel = this.getView().getModel("view");
			var sLog = (oViewModel.getProperty("/input") || "").trim();
			if (!sLog) {
				MessageToast.show(this._text("emptyLog"));
				return;
			}

			var sUrl = this.getOwnerComponent().getModel("config").getProperty("/aiServiceUrl");
			oViewModel.setProperty("/busy", true);

			fetch(sUrl + "/api/explain", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ log: sLog, context: oViewModel.getProperty("/context") })
			}).then(function (oResponse) {
				if (!oResponse.ok) {
					throw new Error("HTTP " + oResponse.status);
				}
				return oResponse.json();
			}).then(function (oResult) {
				oViewModel.setProperty("/result", oResult);
			}).catch(function () {
				MessageBox.error(this._text("serviceDown", [sUrl]));
			}.bind(this)).finally(function () {
				oViewModel.setProperty("/busy", false);
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
