/**
 * Cognito Token Manager for Production Environment
 */
import { CognitoUserPool, CognitoUser } from 'amazon-cognito-identity-js';

const userPool = new CognitoUserPool({
  UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
  ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
});

export const cognitoTokenManager = {
  /**
   * Get current Cognito session and return ID token
   */
  async getAccessToken(): Promise<string | null> {
    return new Promise((resolve) => {
      const cognitoUser = userPool.getCurrentUser();
      
      if (cognitoUser) {
        cognitoUser.getSession((err: any, session: any) => {
          if (err || !session) {
            resolve(null);
          } else {
            // Use Access token for API calls (required by backend)
            resolve(session.getAccessToken().getJwtToken());
          }
        });
      } else {
        resolve(null);
      }
    });
  },

  /**
   * Check if user has valid session
   */
  async hasValidSession(): Promise<boolean> {
    const token = await this.getAccessToken();
    return !!token;
  },

  /**
   * Clear Cognito session
   */
  clearTokens(): void {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }
  }
};
