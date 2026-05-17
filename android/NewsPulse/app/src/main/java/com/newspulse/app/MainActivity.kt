package com.newspulse.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.newspulse.app.data.AuthStore
import com.newspulse.app.data.RetrofitClient
import com.newspulse.app.ui.*
import kotlinx.coroutines.runBlocking

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val authStore = AuthStore(this)
        val api = RetrofitClient.create(this)

        val isLoggedIn = runBlocking { authStore.getToken() != null }

        setContent {
            MaterialTheme {
                val navController = rememberNavController()
                val startDest = if (isLoggedIn) "feed" else "auth"

                Scaffold(
                    bottomBar = {
                        if (isLoggedIn) {
                            NavigationBar {
                                NavigationBarItem(
                                    selected = false,
                                    onClick = { navController.navigate("feed") { popUpTo("feed") { inclusive = true } } },
                                    icon = { Text("📰", textAlign = TextAlign.Center) },
                                    label = { Text("每日精选") }
                                )
                                NavigationBarItem(
                                    selected = false,
                                    onClick = { navController.navigate("tracking") { popUpTo("tracking") { inclusive = true } } },
                                    icon = { Text("🔔", textAlign = TextAlign.Center) },
                                    label = { Text("消息追踪") }
                                )
                                NavigationBarItem(
                                    selected = false,
                                    onClick = { navController.navigate("settings") { popUpTo("settings") { inclusive = true } } },
                                    icon = { Text("⚙️", textAlign = TextAlign.Center) },
                                    label = { Text("设置") }
                                )
                            }
                        }
                    }
                ) { padding ->
                    NavHost(
                        navController = navController,
                        startDestination = startDest,
                        modifier = Modifier.padding(padding)
                    ) {
                        composable("auth") {
                            AuthScreen(api = api, authStore = authStore, onLoginSuccess = {
                                navController.navigate("feed") { popUpTo("auth") { inclusive = true } }
                            })
                        }
                        composable("feed") {
                            FeedScreen(api = api)
                        }
                        composable("tracking") {
                            TrackingScreen(api = api)
                        }
                        composable("settings") {
                            SettingsScreen(api = api, authStore = authStore, onLogout = {
                                navController.navigate("auth") { popUpTo(0) { inclusive = true } }
                            })
                        }
                    }
                }
            }
        }
    }
}
