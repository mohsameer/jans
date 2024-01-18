package io.jans.kc.api.config.client;

import io.jans.config.api.client.ApiClient;
import io.jans.config.api.client.SamlTrustRelationshipApi;
import io.jans.config.api.client.ApiException;
import io.jans.config.api.client.model.TrustRelationship;
import io.jans.kc.api.config.client.model.JansTrustRelationship;

import java.util.List;
import java.util.stream.Collectors;

public class JansConfigApiClient {

    private SamlTrustRelationshipApi trApi;

    private JansConfigApiClient() {
        
    }

    public boolean trustRelationshipExists(String inum) {

        try {
            TrustRelationship tr = trApi.getTrustRelationshipById(inum);
            return (tr != null);
        }catch(ApiException e) {
            throw new JansConfigApiError("trustRelationshipExists() failed",e);
        }
    }

    public List<JansTrustRelationship> getAllTrustRelationships() {

        try {
            List<TrustRelationship> trlist = trApi.getTrustRelationships();
            return trlist.stream()
                .map(JansConfigApiClient::toJansTrustRelationship)
                .collect(Collectors.toList());
        }catch(ApiException e) {
            throw new JansConfigApiError("getAllTrustRelationships() failed",e);
        }
    }

    public static JansConfigApiClient createInstance(ApiCredentials credentials) {

        JansConfigApiClient client = new JansConfigApiClient();
        client.trApi = newSamlTrustRelationshipApi(credentials);
        return client;
    }

    private static SamlTrustRelationshipApi newSamlTrustRelationshipApi(ApiCredentials credentials) {

        SamlTrustRelationshipApi ret = new SamlTrustRelationshipApi();
        ret.setApiClient(createApiClient(credentials));
        return ret;
    }

    private static ApiClient createApiClient(ApiCredentials credentials) {

        ApiClient apiclient = new ApiClient();
        apiclient.setAccessToken(credentials.bearerToken());
        return apiclient;
    }

    private static JansTrustRelationship toJansTrustRelationship(TrustRelationship tr) {

        JansTrustRelationship ret = new JansTrustRelationship(tr);
        return ret;
    }
}
