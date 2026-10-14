sap.ui.define([
	"sap/ui/core/UIComponent",
	"sap/ui/model/json/JSONModel",
	"./util/ErrorLog"
], function (UIComponent, JSONModel, ErrorLog) {
	"use strict";

	return UIComponent.extend("logsense.Component", {
		metadata: {
			manifest: "json",
			interfaces: ["sap.ui.core.IAsyncContentCreation"]
		},

		init: function () {
			UIComponent.prototype.init.apply(this, arguments);

			// Where the AI log-explainer service runs (see ai-service/)
			this.setModel(new JSONModel({ aiServiceUrl: "http://localhost:8000" }), "config");

			// Central error log: every failed OData call is captured here for troubleshooting
			this._errorLog = new ErrorLog();
			this._errorLog.attachTo(this.getModel());
			this.setModel(this._errorLog.getModel(), "log");

			this.getRouter().initialize();
		},

		getErrorLog: function () {
			return this._errorLog;
		},

		destroy: function () {
			if (this._errorLog) {
				this._errorLog.destroy();
			}
			UIComponent.prototype.destroy.apply(this, arguments);
		}
	});
});
