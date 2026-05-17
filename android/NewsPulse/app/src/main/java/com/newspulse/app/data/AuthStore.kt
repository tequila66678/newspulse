package com.newspulse.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth")

class AuthStore(private val context: Context) {
    companion object {
        val TOKEN_KEY = stringPreferencesKey("access_token")
        val EMAIL_KEY = stringPreferencesKey("email")
    }

    val token: Flow<String?> = context.dataStore.data.map { it[TOKEN_KEY] }
    val email: Flow<String?> = context.dataStore.data.map { it[EMAIL_KEY] }

    suspend fun saveAuth(token: String, email: String) {
        context.dataStore.edit {
            it[TOKEN_KEY] = token
            it[EMAIL_KEY] = email
        }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }

    suspend fun getToken(): String? = token.first()
}
