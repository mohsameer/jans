package io.jans.chip.repository

import android.content.Context
import android.util.Log
import io.jans.chip.model.OPConfiguration
import io.jans.chip.retrofit.ApiAdapter
import io.jans.chip.utils.AppConfig
import io.jans.chip.AppDatabase
import retrofit2.Response

class OPConfigurationRepository (context: Context){
    private val TAG = "OPConfigurationRepository"
    private val appDatabase = AppDatabase.getInstance(context);
    private var opConfiguration: OPConfiguration? =
        OPConfiguration("", null, null, null, null, null, null)
    suspend fun fetchOPConfiguration(configurationUrl: String): OPConfiguration? {
        try {
            val issuer: String = configurationUrl.replace(AppConfig.OP_CONFIG_URL, "")
            var response: Response<OPConfiguration> =
                ApiAdapter.getInstance(issuer).getOPConfiguration(configurationUrl)
            if (response.code() != 200) {
                opConfiguration?.isSuccessful = false
                opConfiguration?.errorMessage = "Error in fetching OP configuration."
                return opConfiguration
            }
            opConfiguration = response.body()

            if (!response.isSuccessful || opConfiguration == null) {
                opConfiguration?.isSuccessful = false
                opConfiguration?.errorMessage = "Error in fetching OP configuration."
                return opConfiguration
            }

            opConfiguration?.isSuccessful = true
            opConfiguration?.sno = AppConfig.DEFAULT_S_NO
            appDatabase.opConfigurationDao().deleteAll()
            appDatabase.opConfigurationDao().insert(opConfiguration)
            Log.d(TAG,"Inside fetchOPConfiguration :: opConfiguration :: " + opConfiguration.toString())

            return opConfiguration
        } catch(e: Exception) {
            Log.e(TAG,"Error in fetching OP configuration :: " + e.message)
            opConfiguration?.isSuccessful = false
            opConfiguration?.errorMessage = "Error in fetching OP configuration :: " + e.message
            return opConfiguration
            //e.printStackTrace()
        }
    }

    suspend fun isOPConfigurationInDatabase(): Boolean {
        var opConfigurations: List<OPConfiguration>? = appDatabase?.opConfigurationDao()?.getAll()
        var opConfiguration: OPConfiguration? = null
        if(opConfigurations != null && !opConfigurations.isEmpty()) {
            opConfiguration = opConfigurations?.let { it -> it.get(0) }
            return opConfiguration != null
        }
        return false
    }

    suspend fun getOPConfigurationInDatabase(): OPConfiguration? {
        var opConfigurations: List<OPConfiguration>? = appDatabase.opConfigurationDao().getAll()
        var opConfiguration: OPConfiguration? = null
        if(opConfigurations != null && !opConfigurations.isEmpty()) {
            opConfiguration = opConfigurations?.let { it -> it.get(0) }
        }
        return opConfiguration
    }

    suspend fun deleteOPConfigurationInDatabase() {
        appDatabase.opConfigurationDao().deleteAll()
    }

}