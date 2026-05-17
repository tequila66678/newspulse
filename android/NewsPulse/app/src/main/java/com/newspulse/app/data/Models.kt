package com.newspulse.app.data

import com.google.gson.annotations.SerializedName

data class LoginRequest(val email: String, val password: String)
data class RegisterRequest(val email: String, val password: String)
data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    val user: UserResponse
)
data class UserResponse(val id: Int, val email: String, @SerializedName("created_at") val createdAt: String)
data class FcmTokenUpdate(@SerializedName("fcm_token") val fcmToken: String)

data class SubscriptionRequest(val keyword: String, val type: String = "topic")
data class SubscriptionResponse(
    val id: Int,
    @SerializedName("user_id") val userId: Int,
    val keyword: String,
    val type: String,
    @SerializedName("created_at") val createdAt: String
)

data class ArticleResponse(
    val id: Int,
    val title: String,
    val summary: String?,
    val source: String,
    @SerializedName("source_url") val sourceUrl: String,
    @SerializedName("published_at") val publishedAt: String?,
    val score: Double
)

data class NotificationResponse(
    val id: Int,
    @SerializedName("article_id") val articleId: Int,
    val type: String,
    @SerializedName("sent_at") val sentAt: String,
    val read: Boolean,
    val article: ArticleResponse?
)

data class ListResponse<T>(
    val items: List<T>,
    val total: Int
)
