sap.ui.define([
	"sap/ui/base/Object",
	"sap/ui/model/json/JSONModel"
], function (BaseObject, JSONModel) {
	"use strict";

	var MAX_ENTRIES = 50;
	var MAX_RAW_LENGTH = 4000;

	/**
	 * Captures failed OData requests from a V2 model into a JSON model,
	 * so they can be listed in the UI and sent to the AI service for analysis.
	 */
	return BaseObject.extend("logsense.util.ErrorLog", {
		constructor: function () {
			BaseObject.call(this);
			this._model = new JSONModel({ entries: [] });
		},

		getModel: function () {
			return this._model;
		},

		attachTo: function (oODataModel) {
			oODataModel.attachMetadataFailed(function (oEvent) {
				this.add("Metadata", oEvent.getParameters());
			}, this);
			oODataModel.attachRequestFailed(function (oEvent) {
				this.add("Request", oEvent.getParameter("response") || oEvent.getParameters());
			}, this);
		},

		add: function (sKind, oResponse) {
			oResponse = oResponse || {};
			var sRaw = String(oResponse.responseText || "");
			var sMessage = oResponse.message || "";

			// SAP Gateway / OData V2 error bodies look like {"error":{"code":..,"message":{"value":..}}}
			try {
				var oBody = JSON.parse(sRaw);
				if (oBody.error && oBody.error.message) {
					sMessage = oBody.error.message.value || oBody.error.message;
				}
			} catch (e) {
				// Body was XML or plain text; keep the raw text
			}

			var aEntries = this._model.getProperty("/entries");
			aEntries.unshift({
				timestamp: new Date().toISOString(),
				kind: sKind,
				statusCode: String(oResponse.statusCode || ""),
				statusText: oResponse.statusText || "",
				message: sMessage || "Unknown error",
				raw: sRaw.slice(0, MAX_RAW_LENGTH)
			});
			this._model.setProperty("/entries", aEntries.slice(0, MAX_ENTRIES));
		},

		toText: function (oEntry) {
			return [
				"Timestamp: " + oEntry.timestamp,
				"Source: OData " + oEntry.kind + " (SAP UI5 ODataModel V2)",
				"HTTP " + oEntry.statusCode + " " + oEntry.statusText,
				"Message: " + oEntry.message,
				"Raw response:",
				oEntry.raw
			].join("\n");
		},

		destroy: function () {
			this._model.destroy();
			BaseObject.prototype.destroy.apply(this, arguments);
		}
	});
});
