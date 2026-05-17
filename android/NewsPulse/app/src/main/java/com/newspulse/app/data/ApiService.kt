package com.newspulse.app.data

import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): Response<TokenResponse>

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): Response<TokenResponse>

    @PATCH("auth/me/fcm-token")
    suspend fun updateFcmToken(@Body body: FcmTokenUpdate): Response<Map<String, Any>>

    @GET("subscriptions")
    suspend fun listSubscriptions(): Response<ListResponse<SubscriptionResponse>>

    @POST("subscriptions")
    suspend fun createSubscription(@Body body: SubscriptionRequest): Response<SubscriptionResponse>

    @DELETE("subscriptions/{id}")
    suspend fun deleteSubscription(@Path("id") id: Int): Response<Map<String, Any>>

    @GET("articles")
    suspend fun listArticles(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): Response<ListResponse<ArticleResponse>>

    @GET("articles/digest/{date}")
    suspend fun getDailyDigest(@Path("date") date: String): Response<ListResponse<ArticleResponse>>

    @GET("notifications")
    suspend fun listNotifications(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("n_type") type: String = "track"
    ): Response<ListResponse<NotificationResponse>>

    @PATCH("notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") id: Int): Response<Map<String, Any>>
}
