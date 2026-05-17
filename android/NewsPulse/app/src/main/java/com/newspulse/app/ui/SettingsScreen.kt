package com.newspulse.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.newspulse.app.data.*
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(api: ApiService, authStore: AuthStore, onLogout: () -> Unit) {
    var subscriptions by remember { mutableStateOf<List<SubscriptionResponse>>(emptyList()) }
    var newKeyword by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        try {
            val resp = api.listSubscriptions()
            if (resp.isSuccessful) {
                subscriptions = resp.body()?.items ?: emptyList()
            }
        } catch (_: Exception) { }
    }

    suspend fun refreshSubs() {
        try {
            val resp = api.listSubscriptions()
            if (resp.isSuccessful) {
                subscriptions = resp.body()?.items ?: emptyList()
            }
        } catch (_: Exception) { }
    }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("订阅管理", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 12.dp))

        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = newKeyword,
                onValueChange = { newKeyword = it },
                label = { Text("关键词") },
                modifier = Modifier.weight(1f)
            )
            Spacer(Modifier.width(8.dp))
            IconButton(onClick = {
                if (newKeyword.isNotBlank()) {
                    scope.launch {
                        try {
                            api.createSubscription(SubscriptionRequest(newKeyword.trim()))
                            newKeyword = ""
                            refreshSubs()
                        } catch (_: Exception) { }
                    }
                }
            }) {
                Icon(Icons.Default.Add, contentDescription = "添加")
            }
        }

        Spacer(Modifier.height(12.dp))

        LazyColumn {
            items(subscriptions) { sub ->
                Row(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("${sub.keyword} (${sub.type})")
                    IconButton(onClick = {
                        scope.launch {
                            try {
                                api.deleteSubscription(sub.id)
                                refreshSubs()
                            } catch (_: Exception) { }
                        }
                    }) {
                        Icon(Icons.Default.Delete, contentDescription = "删除")
                    }
                }
            }
        }

        Spacer(Modifier.weight(1f))
        OutlinedButton(
            onClick = { scope.launch { authStore.clear(); onLogout() } },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("退出登录")
        }
    }
}
