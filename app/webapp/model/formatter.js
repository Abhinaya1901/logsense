sap.ui.define([
	"sap/ui/core/library"
], function (coreLibrary) {
	"use strict";

	var ValueState = coreLibrary.ValueState;

	return {
		stockState: function (iUnits, iReorderLevel) {
			if (iUnits === 0) {
				return ValueState.Error;
			}
			if (iUnits <= iReorderLevel) {
				return ValueState.Warning;
			}
			return ValueState.Success;
		},

		discontinuedState: function (bDiscontinued) {
			return bDiscontinued ? ValueState.Error : ValueState.Success;
		},

		severityState: function (sSeverity) {
			switch ((sSeverity || "").toLowerCase()) {
				case "high": return ValueState.Error;
				case "medium": return ValueState.Warning;
				case "low": return ValueState.Information;
				default: return ValueState.None;
			}
		}
	};
});
