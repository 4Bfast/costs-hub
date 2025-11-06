/**
 * Cognito Authentication Integration - Direct API
 */
import { 
  CognitoUserPool, 
  CognitoUser, 
  AuthenticationDetails,
  CognitoUserSession
} from 'amazon-cognito-identity-js';

const COGNITO_CONFIG = {
  userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
  clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
  domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN!,
};

const userPool = new CognitoUserPool({
  UserPoolId: COGNITO_CONFIG.userPoolId,
  ClientId: COGNITO_CONFIG.clientId,
});

export const cognitoAuth = {
  /**
   * Direct sign in with email/password (no redirect)
   */
  signIn(email: string, password: string): Promise<CognitoUserSession> {
    return new Promise((resolve, reject) => {
      const authenticationDetails = new AuthenticationDetails({
        Username: email,
        Password: password,
      });

      const cognitoUser = new CognitoUser({
        Username: email,
        Pool: userPool,
      });

      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (session: CognitoUserSession) => {
          console.log('✅ Cognito authentication successful');
          resolve(session);
        },
        onFailure: (err) => {
          console.error('❌ Cognito authentication failed:', err);
          reject(err);
        },
        newPasswordRequired: (userAttributes, requiredAttributes) => {
          console.log('🔄 New password required');
          reject(new Error('New password required. Please reset your password.'));
        },
      });
    });
  },

  /**
   * Get current user session
   */
  getCurrentSession(): Promise<CognitoUserSession | null> {
    return new Promise((resolve) => {
      const cognitoUser = userPool.getCurrentUser();
      
      if (cognitoUser) {
        cognitoUser.getSession((err: any, session: CognitoUserSession) => {
          if (err) {
            resolve(null);
          } else {
            resolve(session);
          }
        });
      } else {
        resolve(null);
      }
    });
  },

  /**
   * Sign out current user
   */
  signOut(): void {
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }
  },

  /**
   * Get user attributes
   */
  getUserAttributes(): Promise<any> {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      
      if (cognitoUser) {
        cognitoUser.getSession((err: any, session: CognitoUserSession) => {
          if (err) {
            reject(err);
          } else {
            cognitoUser.getUserAttributes((err, attributes) => {
              if (err) {
                reject(err);
              } else {
                const userInfo: any = {};
                attributes?.forEach(attr => {
                  userInfo[attr.getName()] = attr.getValue();
                });
                resolve(userInfo);
              }
            });
          }
        });
      } else {
        reject(new Error('No current user'));
      }
    });
  },

  // Legacy methods for backward compatibility
  login(): void {
    console.warn('⚠️ cognitoAuth.login() is deprecated. Use signIn() instead.');
  },

  logout(): void {
    this.signOut();
  },
};
