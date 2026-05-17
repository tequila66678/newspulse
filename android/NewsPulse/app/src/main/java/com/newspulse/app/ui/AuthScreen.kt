package com.newspulse.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.newspulse.app.data.*
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(
    api: ApiService,
    authStore: AuthStore,
    onLoginSuccess: () -> Unit
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isRegister by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "NewsPulse",
            style = MaterialTheme.typography.headlineLarge,
            modifier = Modifier.padding(bottom = 32.dp)
        )

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("邮箱") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("密码") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(16.dp))

        error?.let {
            Text(it, color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(8.dp))
        }

        Button(
            onClick = {
                loading = true
                error = null
                scope.launch {
                    try {
                        val resp = if (isRegister) {
                            api.register(RegisterRequest(email, password))
                        } else {
                            api.login(LoginRequest(email, password))
                        }
                        if (resp.isSuccessful) {
                            val body = resp.body()!!
                            authStore.saveAuth(body.accessToken, body.user.email)
                            onLoginSuccess()
                        } else {
                            error = if (isRegister) "注册失败" else "登录失败"
                        }
                    } catch (e: Exception) {
                        error = "网络错误: ${e.message}"
                    }
                    loading = false
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !loading
        ) {
            Text(if (isRegister) "注册" else "登录")
        }

        TextButton(onClick = { isRegister = !isRegister }) {
            Text(if (isRegister) "已有账号？登录" else "没有账号？注册")
        }
    }
}
